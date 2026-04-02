"""
B2B Billing API Router

Endpoints for B2B tenant billing and subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
import logging
import stripe

from core.db.session import get_db
from modules.b2b.middleware.b2b_auth import get_current_active_user
from modules.b2b.rbac.decorators import require_permission
from modules.b2b.services.subscription_service import SubscriptionService
from modules.b2b.services.invoice_service import InvoiceService
from modules.b2b.services.tenant_service import tenant_service
from modules.b2b.models import SubscriptionTier, InvoiceStatus
from workers.b2b_worker.email_tasks import send_payment_failure_alert
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["B2B Billing"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CheckoutRequest(BaseModel):
    tier: str  # 'professional' | 'enterprise'
    billing_interval: str = 'monthly'  # 'monthly' | 'yearly'
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_session_id: str
    checkout_url: str
    seat_count: int
    pricing: dict


class SubscriptionResponse(BaseModel):
    id: str
    tenant_id: str
    tier: str
    payment_mode: str
    status: str
    seat_count: int
    base_price_cents: int
    per_seat_price_cents: int
    total_amount_cents: int
    currency: str
    billing_interval: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    payment_method_info: Optional[dict] = None  # {card_brand, card_last4}


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    status: str
    amount_due: int
    amount_paid: int
    currency: str
    seat_count_snapshot: int
    invoice_date: str
    due_date: Optional[str]
    paid_at: Optional[str]
    billing_period_start: str
    billing_period_end: str
    invoice_pdf_url: Optional[str]


# ============================================================================
# Subscription Endpoints
# ============================================================================

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user=require_permission("billing", "read"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current subscription for the tenant.
    Returns starter tier if no subscription exists.
    Requires billing:read permission (Admin/Owner).
    """
    # current_user is a UserModel object with tenant_id attribute
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    service = SubscriptionService(db)
    
    sub_data = await service.get_subscription_details(tenant_id)
    
    return SubscriptionResponse(
        id=sub_data['id'],
        tenant_id=sub_data['tenant_id'],
        tier=sub_data['tier'],
        payment_mode=sub_data['payment_mode'],
        status=sub_data['status'],
        seat_count=sub_data['seat_count'],
        base_price_cents=sub_data['base_price_cents'],
        per_seat_price_cents=sub_data['per_seat_price_cents'],
        total_amount_cents=sub_data['total_amount_cents'],
        currency=sub_data['currency'],
        billing_interval=sub_data['billing_interval'],
        current_period_start=sub_data['current_period_start'],
        current_period_end=sub_data['current_period_end'],
        payment_method_info=sub_data['payment_method_info']
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user=require_permission("billing", "manage"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe checkout session for subscription upgrade.
    Only for card-based payments (professional, enterprise tiers).
    Requires billing:manage permission (Owner only).
    """
    tenant_id = current_user.get('tenant_id') if isinstance(current_user, dict) else current_user.tenant_id
    try:
        tier = SubscriptionTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}")
    
    if tier == SubscriptionTier.STARTER:
        raise HTTPException(status_code=400, detail="Starter tier is free, no checkout needed")
    
    service = SubscriptionService(db)
    
    try:
        result = await service.create_checkout_session(
            tenant_id=tenant_id,
            tier=tier,
            billing_interval=request.billing_interval,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        return CheckoutResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create checkout session. Please try again or contact support.")


class PortalSessionRequest(BaseModel):
    return_url: Optional[str] = None

@router.post("/portal", response_model=dict)
async def create_portal_session(
    request: PortalSessionRequest = None,
    current_user=require_permission("billing", "manage"),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session.
    Returns a URL to redirect the user to.
    Requires billing:manage permission.
    """
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    service = SubscriptionService(db)
    
    # Default return URL
    default_return_url = f"{settings.frontend_url}/billing"
    
    # Use requested return URL if valid and safe
    return_url = default_return_url
    if request and request.return_url:
        # Security check: Ensure return_url belongs to our frontend
        if request.return_url.startswith(settings.frontend_url):
            return_url = request.return_url
        else:
             logger.warning(f"Ignored unsafe return_url: {request.return_url}")
    
    try:
        portal_url = await service.create_portal_session(
            tenant_id=tenant_id,
            return_url=return_url
        )
        return {"url": portal_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Portal creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create portal session. Please try again or contact support.")


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = None,
    limit: int = 50,
    current_user=require_permission("billing", "read"),
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices for the current tenant.
    Requires billing:read permission (Admin/Owner).
    """
    tenant_id = current_user.get('tenant_id') if isinstance(current_user, dict) else current_user.tenant_id
    service = InvoiceService(db)
    
    status_filter = None
    if status:
        try:
            status_filter = InvoiceStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    invoices = await service.list_invoices(
        tenant_id=tenant_id,
        status=status_filter,
        limit=limit
    )
    
    return [
        InvoiceResponse(
            id=str(inv.id),
            invoice_number=inv.invoice_number,
            status=inv.status,
            amount_due=inv.amount_due,
            amount_paid=inv.amount_paid,
            currency=inv.currency,
            seat_count_snapshot=inv.seat_count_snapshot,
            invoice_date=inv.invoice_date.isoformat(),
            due_date=inv.due_date.isoformat() if inv.due_date else None,
            paid_at=inv.paid_at.isoformat() if inv.paid_at else None,
            billing_period_start=inv.billing_period_start.isoformat(),
            billing_period_end=inv.billing_period_end.isoformat(),
            invoice_pdf_url=inv.invoice_pdf_url
        )
        for inv in invoices
    ]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    current_user=require_permission("billing", "read"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific invoice details.
    RLS will enforce tenant isolation.
    Requires billing:read permission (Admin/Owner).
    """
    service = InvoiceService(db)
    invoice = await service.get_invoice_by_id(invoice_id)
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return InvoiceResponse(
        id=str(invoice.id),
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        amount_due=invoice.amount_due,
        amount_paid=invoice.amount_paid,
        currency=invoice.currency,
        seat_count_snapshot=invoice.seat_count_snapshot,
        invoice_date=invoice.invoice_date.isoformat(),
        due_date=invoice.due_date.isoformat() if invoice.due_date else None,
        paid_at=invoice.paid_at.isoformat() if invoice.paid_at else None,
        billing_period_start=invoice.billing_period_start.isoformat(),
        billing_period_end=invoice.billing_period_end.isoformat(),
        invoice_pdf_url=invoice.invoice_pdf_url
    )


# ============================================================================
# Webhook Handler
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events for B2B subscriptions.
    """
    try:
        payload = await request.body()
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload,
                stripe_signature,
                settings.stripe_b2b_webhook_secret
            )
        except ValueError:
            logger.error("Invalid payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        event_type = event['type']
        data = event['data']['object']
        
        logger.info(f"📥 Received Stripe webhook: {event_type}")
        logger.debug(f"Webhook data: {data}")
        
        # Handle different event types
        subscription_service = SubscriptionService(db)
        invoice_service = InvoiceService(db)
        
        # Set platform admin context to bypass RLS for system operations (like B2C does)
        from core.db.rls import rls_service
        await rls_service.set_platform_admin_context(db)
        
        if event_type == 'checkout.session.completed':
            logger.info(f"💳 Processing checkout completion...")
            try:
                subscription = await subscription_service.handle_checkout_completed(data)
                await db.commit()
                logger.info(f"✅ Subscription updated successfully: {subscription.id}, tier: {subscription.tier}")
            except Exception as e:
                logger.error(f"❌ Failed to process checkout: {e}", exc_info=True)
                await db.rollback()
                raise
            
        elif event_type == 'customer.subscription.updated':
            logger.info(f"🔄 Processing subscription update...")
            # Handle subscription updates (renewals, cancellations)
            subscription = await subscription_service.get_tenant_subscription(
                UUID(data.get('metadata', {}).get('tenant_id'))
            )
            if subscription:
                # Update subscription details from Stripe
                pass  # TODO: Implement subscription update logic
            
        elif event_type == 'invoice.paid':
            logger.info(f"💰 Processing invoice payment...")
            logger.info(f"Invoice data subscription field: {data.get('subscription')}")
            logger.info(f"Invoice ID: {data.get('id')}")
            try:
                # Sync Stripe invoice
                await invoice_service.sync_stripe_invoice(data)
                await db.commit()
            except ValueError as e:
                # Subscription not found - race condition where invoice.paid arrived before checkout.session.completed
                # Return 200 so Stripe will retry this webhook later
                logger.warning(f"Skipping invoice sync (will retry): {e}")
                await db.rollback()
                return {"status": "deferred", "message": str(e)}
            
        elif event_type == 'invoice.payment_failed':
            logger.warning(f"⚠️ Processing payment failure...")
            try:
                invoice = await invoice_service.sync_stripe_invoice(data)
                await db.commit()
            except ValueError as e:
                # Same race condition handling
                logger.warning(f"Skipping invoice sync (will retry): {e}")
                await db.rollback()
                return {"status": "deferred", "message": str(e)}

            try:
                send_payment_failure_alert.delay(
                    tenant_id=str(invoice.tenant_id),
                    invoice_id=str(invoice.id),
                )
            except Exception as e:
                logger.error(f"Failed to queue payment failure alert: {e}", exc_info=True)
        else:
            logger.info(f"ℹ️ Unhandled event type: {event_type}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# ============================================================================
# Billing Profile Endpoints
# ============================================================================



class BillingProfileResponse(BaseModel):
    tax_id: Optional[str] = None
    vat_number: Optional[str] = None
    billing_address: Optional[str] = None
    billing_email: Optional[str] = None

class BillingProfileUpdate(BaseModel):
    tax_id: Optional[str] = None
    vat_number: Optional[str] = None
    billing_address: Optional[dict] = None
    billing_email: Optional[str] = None

@router.get("/profile", response_model=BillingProfileResponse)
async def get_billing_profile(
    current_user=require_permission("billing", "read"),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    try:
        profile = await tenant_service.get_billing_profile(db, tenant_id)
        return BillingProfileResponse(**profile)
    except ValueError as e:
        raise HTTPException(404, str(e))

@router.patch("/profile", response_model=BillingProfileResponse)
async def update_billing_profile(
    payload: BillingProfileUpdate,
    current_user=require_permission("billing", "manage"),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    
    try:
        updated_profile = await tenant_service.update_billing_profile(
            db=db,
            tenant_id=tenant_id,
            tax_id=payload.tax_id,
            vat_number=payload.vat_number,
            billing_address=payload.billing_address,
            billing_email=payload.billing_email
        )
        return BillingProfileResponse(**updated_profile)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ============================================================================
# Invoices Endpoints  
