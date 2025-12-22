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
from services.b2b.middleware.b2b_auth import get_current_active_user
from services.b2b.rbac.decorators import require_permission
from services.b2b.services.subscription_service import SubscriptionService
from services.b2b.services.invoice_service import InvoiceService
from services.b2b.models import SubscriptionTier, InvoiceStatus
from core.config import settings

logger = logging.getLogger(__name__)

router =APIRouter(prefix="/api/b2b/billing", tags=["B2B Billing"])


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
    subscription = await service.get_tenant_subscription(tenant_id)
    
    if not subscription:
        # Return default starter tier info
        seat_count = await service.get_active_seat_count(tenant_id)
        # Fetch starter plan for default pricing
        plan = await service.get_plan_by_tier_key(SubscriptionTier.STARTER.value)
        pricing = await service.calculate_seat_based_pricing(
            plan,
            seat_count,
            'monthly'
        )
        
        return SubscriptionResponse(
            id="",
            tenant_id=str(tenant_id),
            tier="starter",
            payment_mode="card",
            status="active",
            seat_count=seat_count,
            base_price_cents=pricing['base_price_cents'],
            per_seat_price_cents=pricing['per_seat_price_cents'],
            total_amount_cents=pricing['total_amount_cents'],
            currency="USD",
            billing_interval="monthly",
            current_period_start=None,
            current_period_end=None,
            payment_method_info=None
        )
    

    # Fetch payment method info from Stripe if card payment
    payment_method_info = None
    if subscription.payment_mode == 'card' and subscription.provider_subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription.provider_subscription_id)
            
            # 1. Check Subscription default payment method
            pm_id = stripe_sub.default_payment_method
            
            # 2. If not on subscription, check Customer default payment method
            if not pm_id and stripe_sub.customer:
                customer = stripe.Customer.retrieve(stripe_sub.customer)
                if customer.invoice_settings and customer.invoice_settings.default_payment_method:
                    pm_id = customer.invoice_settings.default_payment_method
            
            if pm_id:
                # Handle case where pm_id might be an object if expanded (unlikely here but safe)
                if isinstance(pm_id, str):
                    pm = stripe.PaymentMethod.retrieve(pm_id)
                else:
                    pm = pm_id
                    
                if pm.type == 'card':
                    payment_method_info = {
                        'card_brand': pm.card.brand,
                        'card_last4': pm.card.last4,
                        'exp_year': pm.card.exp_year
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch payment method from Stripe: {e}")
    
    return SubscriptionResponse(
        id=str(subscription.id),
        tenant_id=str(subscription.tenant_id),
        tier=subscription.tier,
        payment_mode=subscription.payment_mode,
        status=subscription.status,
        seat_count=subscription.seat_count,
        base_price_cents=subscription.base_price_cents,
        per_seat_price_cents=subscription.per_seat_price_cents,
        total_amount_cents=subscription.total_amount_cents,
        currency=subscription.currency,
        billing_interval=subscription.billing_interval,
        current_period_start=subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        payment_method_info=payment_method_info
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
        logger.error(f"Checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


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
        logger.error(f"Portal creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = None,
    limit: int = 50,
    current_user=require_permission("invoices", "read"),
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices for the current tenant.
    Requires invoices:read permission (Admin/Owner).
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
    current_user=require_permission("invoices", "read"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific invoice details.
    RLS will enforce tenant isolation.
    Requires invoices:read permission (Admin/Owner).
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
            # Sync Stripe invoice
            await invoice_service.sync_stripe_invoice(data)
            await db.commit()
            
        elif event_type == 'invoice.payment_failed':
            logger.warning(f"⚠️ Processing payment failure...")
            await invoice_service.sync_stripe_invoice(data)
            await db.commit()
            # TODO: Send payment failure notification
        else:
            logger.info(f"ℹ️ Unhandled event type: {event_type}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
    billing_address: Optional[str] = None
    billing_email: Optional[str] = None

@router.get("/profile", response_model=BillingProfileResponse)
async def get_billing_profile(
    current_user=require_permission("billing", "read"),
    db: AsyncSession = Depends(get_db)
):
    from services.b2b.models import TenantModel
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    # helper to extract address string from JSONB
    addr_str = None
    if tenant.billing_address:
        if isinstance(tenant.billing_address, dict):
             # Try to find common keys or return dumped string? 
             # Let's assume we want a single string field 'text' or fallback
             addr_str = tenant.billing_address.get('text', '') or tenant.billing_address.get('address', '')
             if not addr_str and tenant.billing_address:
                 # If dict is not empty but no key match, convert values to string? 
                 # Or just return empty string to clear the error.
                 # Let's return empty string if structure is unknown to allow user to overwrite in UI
                 pass
        elif isinstance(tenant.billing_address, str):
            addr_str = tenant.billing_address
        
    return BillingProfileResponse(
        tax_id=tenant.tax_id,
        vat_number=tenant.vat_number,
        billing_address=addr_str,
        billing_email=tenant.billing_email
    )

@router.patch("/profile", response_model=BillingProfileResponse)
async def update_billing_profile(
    payload: BillingProfileUpdate,
    current_user=require_permission("billing", "manage"),
    db: AsyncSession = Depends(get_db)
):
    from services.b2b.models import TenantModel
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    tenant = await db.get(TenantModel, tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    
    # Update fields if provided (allow empty string to clear?)
    if payload.tax_id is not None: tenant.tax_id = payload.tax_id
    if payload.vat_number is not None: tenant.vat_number = payload.vat_number
    
    if payload.billing_address is not None: 
        # Store as structured JSON
        tenant.billing_address = {"text": payload.billing_address}
        
    if payload.billing_email is not None: tenant.billing_email = payload.billing_email
    
    await db.commit()
    
    addr_str = None
    if tenant.billing_address and isinstance(tenant.billing_address, dict):
        addr_str = tenant.billing_address.get('text')

    return BillingProfileResponse(
        tax_id=tenant.tax_id,
        vat_number=tenant.vat_number,
        billing_address=addr_str,
        billing_email=tenant.billing_email
    )

