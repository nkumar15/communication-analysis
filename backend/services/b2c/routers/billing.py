"""
Billing API Router

Endpoints for subscription checkout, management, and invoice retrieval.
Uses async SQLAlchemy patterns for compatibility with AsyncSession.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from core.database import get_db
from services.b2c.middleware.b2c_auth import get_current_b2c_user
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace
from services.b2c.models.subscription import Subscription, Invoice
from services.b2c.services.subscription_service import SubscriptionService
from services.b2c.services.coupon_service import (
    CouponService,
    CouponError,
    CouponNotFoundError,
    CouponExpiredError,
    CouponAlreadyRedeemedError,
    CouponMaxRedemptionsError,
    CouponNotApplicableError
)
from core.payment import PaymentProviderFactory
from core.config import settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def get_user_id(user) -> str:
    """Extract user ID from either a dict or object."""
    if isinstance(user, dict):
        return user.get('id')
    return user.id


router = APIRouter(prefix="/api/b2c/billing", tags=["B2C Billing"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CheckoutRequest(BaseModel):
    workspace_id: str
    tier: str  # 'premium' | 'ultimate'
    billing_interval: str = 'monthly'  # 'monthly' | 'yearly'
    coupon_code: Optional[str] = None  # Optional coupon code
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_session_id: str
    checkout_url: str


class SubscriptionResponse(BaseModel):
    id: str
    workspace_id: str
    tier: str
    billing_interval: str
    status: str
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    amount_cents: int
    currency: str


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    portal_url: str


# ============================================================================
# Subscription Endpoints
# ============================================================================

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription purchase.
    """
    try:
        # Get workspace
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == request.workspace_id,
                Workspace.owner_id == get_user_id(current_user)
            )
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
        
        # Validate tier
        if request.tier not in ['premium', 'ultimate']:
            raise HTTPException(status_code=400, detail="Invalid tier. Must be 'premium' or 'ultimate'")
        
        if request.billing_interval not in ['monthly', 'yearly']:
            raise HTTPException(status_code=400, detail="Invalid billing interval")
        
        # Create checkout session
        service = SubscriptionService(db)
        result = await service.create_checkout_session(
            user=current_user,
            workspace=workspace,
            tier=request.tier,
            billing_interval=request.billing_interval,
            coupon_code=request.coupon_code,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        
        return CheckoutResponse(**result)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace_id: str,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current subscription for a workspace.
    """
    # Get workspace
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.owner_id == get_user_id(current_user)
        )
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    # Get subscription
    service = SubscriptionService(db)
    subscription = await service.get_subscription(workspace)
    
    if not subscription:
        # Return free tier info
        return SubscriptionResponse(
            id="free",
            workspace_id=workspace_id,
            tier="free",
            billing_interval="none",
            status="active",
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
            amount_cents=0,
            currency="USD"
        )
    
    return SubscriptionResponse(
        id=str(subscription.id),
        workspace_id=str(subscription.workspace_id),
        tier=subscription.plan.tier_key if subscription.plan else "free",
        billing_interval=subscription.billing_interval or "monthly",
        status=subscription.status,
        current_period_start=subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        cancel_at_period_end=subscription.cancel_at_period_end or False,
        amount_cents=subscription.amount_cents or 0,
        currency=subscription.currency or "USD"
    )


@router.post("/cancel")
async def cancel_subscription(
    workspace_id: str,
    immediate: bool = False,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a subscription.
    """
    try:
        # Get workspace
        result = await db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.owner_id == get_user_id(current_user)
            )
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found or access denied")
        
        service = SubscriptionService(db)
        subscription = await service.cancel_subscription(workspace, immediate=immediate)
        
        return {
            "success": True,
            "subscription_id": str(subscription.id),
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session for self-service billing.
    """
    try:
        service = SubscriptionService(db)
        portal_url = await service.create_customer_portal_session(
            user=current_user,
            return_url=request.return_url
        )
        
        return PortalResponse(portal_url=portal_url)
        
    except Exception as e:
        logger.error(f"Error creating portal session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


# ============================================================================
# Invoice Endpoints
# ============================================================================

@router.get("/invoices")
async def list_invoices(
    limit: int = 10,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices for the current user.
    """
    result = await db.execute(
        select(Invoice)
        .where(Invoice.user_id == get_user_id(current_user))
        .order_by(Invoice.created_at.desc())
        .limit(limit)
    )
    invoices = result.scalars().all()
    
    return {
        "invoices": [
            {
                "id": str(inv.id),
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "currency": inv.currency,
                "status": inv.status,
                "invoice_pdf_url": inv.invoice_pdf_url,
                "hosted_invoice_url": inv.hosted_invoice_url,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None
            }
            for inv in invoices
        ]
    }


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific invoice.
    """
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.user_id == get_user_id(current_user)
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {
        "id": str(invoice.id),
        "subscription_id": str(invoice.subscription_id) if invoice.subscription_id else None,
        "amount_due": invoice.amount_due,
        "amount_paid": invoice.amount_paid,
        "currency": invoice.currency,
        "status": invoice.status,
        "invoice_pdf_url": invoice.invoice_pdf_url,
        "hosted_invoice_url": invoice.hosted_invoice_url,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None
    }


@router.get("/invoices/{invoice_id}/download")
async def download_invoice(
    invoice_id: str,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download invoice PDF.
    """
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.user_id == get_user_id(current_user)
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if not invoice.invoice_pdf_url:
        raise HTTPException(status_code=404, detail="Invoice PDF not available")
    
    return RedirectResponse(url=invoice.invoice_pdf_url)


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
    Handle Stripe webhook events.
    """
    import stripe
    from core.config import settings
    from core.rls import rls_service
    
    # Set platform admin context to bypass RLS for system operations
    await rls_service.set_platform_admin_context(db)
    
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event['type']
    event_data = event['data']['object']
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    service = SubscriptionService(db)
    
    try:
        if event_type == 'checkout.session.completed':
            await service.handle_checkout_completed(event_data)
            
        elif event_type in ['customer.subscription.updated', 'customer.subscription.deleted']:
            await service.handle_subscription_updated(event_data)
            
        elif event_type in ['invoice.paid', 'invoice.payment_failed']:
            await service.sync_invoice(event_data)
            
        else:
            logger.debug(f"Unhandled webhook event: {event_type}")
        
        return JSONResponse(content={"received": True})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Razorpay webhook events.
    """
    # 1. Verify Signature
    # Note: Requires RazorpayProvider implementation in PaymentProviderFactory
    try:
        # Config would ideally come from settings
        config = {'key_id': settings.razorpay_key_id, 'key_secret': settings.razorpay_key_secret}
        provider = PaymentProviderFactory.create('razorpay', config)
        
        payload = await request.body()
        event = await provider.verify_webhook(payload, x_razorpay_signature)
        # event should be normalized: {'event_type': ..., 'data': ...}
        
    except ValueError as e: # Provider not supported yet
        logger.warning(f"Razorpay provider not implemented: {e}")
        raise HTTPException(status_code=501, detail="Razorpay support not fully implemented")
    except Exception as e:
        logger.error(f"Invalid Razorpay webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid request")

    # 2. Process Event
    service = SubscriptionService(db)
    
    try:
        # Map Razorpay events to service calls
        # Assumption: event['data'] is normalized or Service can handle it
        if event['event_type'] == 'subscription.charged': 
            await service.handle_checkout_completed(event['data'], provider_name='razorpay')
            
        elif event['event_type'] in ['subscription.cancelled', 'subscription.paused']:
            await service.handle_subscription_updated(event['data']) # Pass provider?
            
        return JSONResponse(content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing Razorpay webhook: {e}")
        raise HTTPException(status_code=500, detail="Processing failed")


@router.post("/webhooks/xendit")
async def xendit_webhook(
    request: Request,
    x_callback_token: str = Header(None, alias="x-callback-token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Xendit webhook events.
    """
    try:
        config = {'secret_key': settings.xendit_secret_key}
        provider = PaymentProviderFactory.create('xendit', config)
        
        payload = await request.body()
        event = await provider.verify_webhook(payload, x_callback_token)
        
    except ValueError:
        raise HTTPException(status_code=501, detail="Xendit support not implemented")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid request")

    service = SubscriptionService(db)
    # Process event...
    return JSONResponse(content={"status": "ok"})


# ============================================================================
# Coupon Endpoints
# ============================================================================

class ValidateCouponRequest(BaseModel):
    code: str
    tier: Optional[str] = None


class ValidateCouponResponse(BaseModel):
    valid: bool
    code: str
    discount_type: str
    discount_percent: Optional[int]
    discount_amount_cents: Optional[int]
    currency: str
    applicable_tiers: Optional[list]
    description: Optional[str]


@router.post("/coupons/validate", response_model=ValidateCouponResponse)
async def validate_coupon(
    request: ValidateCouponRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate a coupon code.
    """
    try:
        coupon_service = CouponService(db)
        coupon = await coupon_service.validate_coupon(
            code=request.code,
            user=current_user,
            tier=request.tier
        )
        
        return ValidateCouponResponse(
            valid=True,
            code=coupon.code,
            discount_type=coupon.discount_type,
            discount_percent=coupon.discount_percent,
            discount_amount_cents=coupon.discount_amount_cents,
            currency=coupon.currency or "USD",
            applicable_tiers=coupon.applicable_tiers,
            description=coupon.description
        )
        
    except CouponError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating coupon: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate coupon")


@router.get("/coupons/available")
async def get_available_coupons(
    tier: Optional[str] = None,
    limit: int = 10,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of available promotional coupons.
    """
    coupon_service = CouponService(db)
    coupons = await coupon_service.get_available_coupons(tier=tier, limit=limit)
    
    return {
        "coupons": [
            {
                "code": c.code,
                "description": c.description,
                "discount_type": c.discount_type,
                "discount_percent": c.discount_percent,
                "discount_amount_cents": c.discount_amount_cents,
                "currency": c.currency,
                "applicable_tiers": c.applicable_tiers,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None
            }
            for c in coupons
        ]
    }


@router.get("/coupons/my-redemptions")
async def get_my_redemptions(
    limit: int = 10,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's coupon redemption history.
    """
    coupon_service = CouponService(db)
    redemptions = await coupon_service.get_user_redemptions(current_user, limit=limit)
    
    result = []
    for r in redemptions:
        coupon = await coupon_service.get_coupon_by_id(r.coupon_id)
        result.append({
            "coupon_code": coupon.code if coupon else "Unknown",
            "discount_amount_cents": r.discount_amount_cents,
            "redeemed_at": r.redeemed_at.isoformat()
        })
    
    return {"redemptions": result}
