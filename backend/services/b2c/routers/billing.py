"""
Billing API Router

Endpoints for subscription checkout, management, and invoice retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging

from core.database import get_db
from services.b2c.middleware.b2c_auth import get_current_b2c_user
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace
from services.b2c.services.subscription_service import SubscriptionService
from services.b2c.services.coupon_service import CouponService, CouponError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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
# Endpoints
# ============================================================================

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Checkout session for subscription purchase.
    
    The user will be redirected to Stripe's hosted checkout page.
    After payment, Stripe webhook will activate the subscription.
    """
    try:
        # Get workspace
        workspace = db.query(Workspace).filter(
            Workspace.id == request.workspace_id,
            Workspace.owner_id == current_user.id
        ).first()
        
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
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    workspace_id: str,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    Get current subscription for a workspace.
    """
    # Get workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    # Get subscription
    service = SubscriptionService(db)
    subscription = await service.get_subscription(workspace)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    return SubscriptionResponse(
        id=str(subscription.id),
        workspace_id=str(subscription.workspace_id),
        tier=subscription.tier,
        billing_interval=subscription.billing_interval,
        status=subscription.status,
        current_period_start=subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        cancel_at_period_end=subscription.cancel_at_period_end,
        amount_cents=subscription.amount_cents,
        currency=subscription.currency
    )


@router.post("/subscription/cancel")
async def cancel_subscription(
    workspace_id: str,
    immediate: bool = False,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a subscription.
    
    By default, cancels at the end of the billing period.
    Set immediate=true to cancel immediately.
    """
    # Get workspace
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    
    try:
        service = SubscriptionService(db)
        subscription = await service.cancel_subscription(workspace, immediate=immediate)
        
        return {
            "success": True,
            "subscription_id": str(subscription.id),
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "message": "Subscription will be canceled at period end" if not immediate else "Subscription canceled immediately"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session for self-service billing.
    
    Users can manage payment methods, view invoices, and update subscriptions.
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


@router.get("/invoices")
async def list_invoices(
    limit: int = 10,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    List invoices for the current user.
    """
    from services.b2c.models.subscription import Invoice
    
    invoices = db.query(Invoice).filter(
        Invoice.user_id == current_user.id
    ).order_by(
        Invoice.created_at.desc()
    ).limit(limit).all()
    
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
    db: Session = Depends(get_db)
):
    """
    Get details of a specific invoice.
    """
    from backend.services.b2c.models.subscription import Invoice
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
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
    db: Session = Depends(get_db)
):
    """
    Download invoice PDF.
    
    Redirects to Stripe's hosted invoice PDF URL.
    """
    from services.b2c.models.subscription import Invoice
    from fastapi.responses import RedirectResponse
    
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if not invoice.invoice_pdf_url:
        raise HTTPException(status_code=404, detail="Invoice PDF not available")
    
    # Redirect to Stripe's hosted PDF
    return RedirectResponse(url=invoice.invoice_pdf_url)


# ============================================================================
# Webhook Handler
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    
    This endpoint processes subscription lifecycle events:
    - checkout.session.completed: Activate subscription
    - customer.subscription.updated: Sync subscription changes
    - customer.subscription.deleted: Handle cancellation
    - invoice.payment_succeeded: Record invoice
    - invoice.payment_failed: Handle failed payment
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    try:
        # Get raw body
        payload = await request.body()
        
        # Verify webhook signature
        service = SubscriptionService(db)
        event_data = await service.provider.verify_webhook(
            payload=payload,
            signature=stripe_signature
        )
        
        event_type = event_data['event_type']
        data = event_data['data']
        
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            # Activate subscription after successful checkout
            subscription = await service.handle_checkout_completed(data)
            logger.info(f"Subscription activated: {subscription.id}")
            
            # Queue welcome email
            from workers.b2c_worker.tasks import send_subscription_activated_email
            send_subscription_activated_email.delay(
                user_id=str(subscription.user_id),
                workspace_id=str(subscription.workspace_id)
            )
            
        elif event_type == 'customer.subscription.updated':
            # Sync subscription updates
            subscription = await service.handle_subscription_updated(data)
            if subscription:
                logger.info(f"Subscription updated: {subscription.id}")
            
        elif event_type == 'customer.subscription.deleted':
            # Handle subscription deletion - auto downgrade
            subscription = await service.handle_subscription_updated(data)
            if subscription:
                logger.info(f"Subscription deleted: {subscription.id}")
                
                # Queue downgrade task
                from workers.b2c_worker.tasks import downgrade_workspace_to_free
                downgrade_workspace_to_free.delay(
                    workspace_id=str(subscription.workspace_id),
                    reason="subscription_canceled"
                )
            
        elif event_type == 'invoice.payment_succeeded':
            # Record successful invoice payment
            invoice = await service.sync_invoice(data)
            logger.info(f"Invoice payment succeeded: {invoice.id}")
            
            # Queue receipt email
            if invoice.user_id:
                from workers.b2c_worker.tasks import send_invoice_payment_succeeded_email
                send_invoice_payment_succeeded_email.delay(
                    user_id=str(invoice.user_id),
                    invoice_id=str(invoice.id)
                )
            
        elif event_type == 'invoice.payment_failed':
            # Record failed invoice payment
            invoice = await service.sync_invoice(data)
            logger.warning(f"Invoice payment failed: {invoice.id}")
            
            # Queue payment failure notification
            if invoice.subscription_id:
                from services.b2c.models.subscription import Subscription
                subscription = db.query(Subscription).filter(
                    Subscription.id == invoice.subscription_id
                ).first()
                
                if subscription:
                    from workers.b2c_worker.tasks import send_payment_failure_email
                    send_payment_failure_email.delay(
                        user_id=str(subscription.user_id),
                        workspace_id=str(subscription.workspace_id),
                        grace_period_days=7
                    )
        
        else:
            logger.info(f"Unhandled webhook event: {event_type}")
        
        return JSONResponse(content={"status": "success"})
        
    except ValueError as e:
        # Signature verification failed
        logger.error(f"Webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


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
    applicable_tiers: Optional[list[str]]
    description: Optional[str]


@router.post("/coupons/validate", response_model=ValidateCouponResponse)
async def validate_coupon(
    request: ValidateCouponRequest,
    current_user: B2CUser = Depends(get_current_b2c_user),
    db: Session = Depends(get_db)
):
    """
    Validate a coupon code.
    
    Checks if coupon exists, is active, not expired, and applicable to tier.
    """
    try:
        coupon_service = CouponService(db)
        coupon = coupon_service.validate_coupon(
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
            currency=coupon.currency,
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
    db: Session = Depends(get_db)
):
    """
    Get list of available promotional coupons.
    
    Note: In production, you might want to limit this to specific campaigns.
    """
    coupon_service = CouponService(db)
    coupons = coupon_service.get_available_coupons(tier=tier, limit=limit)
    
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
    db: Session = Depends(get_db)
):
    """
    Get user's coupon redemption history.
    """
    from services.b2c.models.subscription import Coupon
    
    coupon_service = CouponService(db)
    redemptions = coupon_service.get_user_redemptions(current_user, limit=limit)
    
    return {
        "redemptions": [
            {
                "coupon_code": db.query(Coupon).filter(Coupon.id == r.coupon_id).first().code,
                "discount_amount_cents": r.discount_amount_cents,
                "redeemed_at": r.redeemed_at.isoformat()
            }
            for r in redemptions
        ]
    }
