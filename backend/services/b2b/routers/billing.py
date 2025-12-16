"""
B2B Billing API Router

Endpoints for B2B tenant billing and subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
import logging
import stripe

from core.database import get_db
from services.b2b.middleware.b2b_auth import get_current_active_user
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
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current subscription for the tenant.
    Returns starter tier if no subscription exists.
    """
    # current_user is a UserModel object with tenant_id attribute
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else current_user.get('tenant_id')
    service = SubscriptionService(db)
    subscription = await service.get_tenant_subscription(tenant_id)
    
    if not subscription:
        # Return default starter tier info
        seat_count = await service.get_active_seat_count(tenant_id)
        pricing = service.calculate_seat_based_pricing(
            SubscriptionTier.STARTER,
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
            current_period_end=None
        )
    
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
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe checkout session for subscription upgrade.
    Only for card-based payments (professional, enterprise tiers).
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


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = None,
    limit: int = 50,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices for the current tenant.
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
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific invoice details.
    RLS will enforce tenant isolation.
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
        
        logger.info(f"Received Stripe webhook: {event_type}")
        
        # Handle different event types
        subscription_service = SubscriptionService(db)
        invoice_service = InvoiceService(db)
        
        if event_type == 'checkout.session.completed':
            await subscription_service.handle_checkout_completed(data)
            await db.commit()
            
        elif event_type == 'customer.subscription.updated':
            # Handle subscription updates (renewals, cancellations)
            subscription = await subscription_service.get_tenant_subscription(
                UUID(data.get('metadata', {}).get('tenant_id'))
            )
            if subscription:
                # Update subscription details from Stripe
                pass  # TODO: Implement subscription update logic
            
        elif event_type == 'invoice.paid':
            # Sync Stripe invoice
            await invoice_service.sync_stripe_invoice(data)
            await db.commit()
            
        elif event_type == 'invoice.payment_failed':
            await invoice_service.sync_stripe_invoice(data)
            await db.commit()
            # TODO: Send payment failure notification
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
