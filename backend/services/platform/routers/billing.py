"""
Unified Billing Admin Router
Handles billing operations for both B2B and B2C.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union, Dict, Any
from uuid import UUID

from core.database import get_db
# from core.auth.jwt import get_current_active_user  # REMOVED: invalid module and unused
from services.platform.middleware.platform_auth import verify_platform_admin

# ... (Previous imports remain same, just single block replacement for cleanliness if possible, or targeted)
# Let's target the import line definition and router definition

# Services
from services.b2b.services.subscription_service import SubscriptionService as B2BSubscriptionService
from services.b2b.services.coupon_service import B2BCouponService
from services.b2c.services.subscription_service import SubscriptionService as B2CSubscriptionService
from services.b2c.services.coupon_service import CouponService as B2CCouponService

# Models
from services.b2b.models import TenantModel, B2BSubscription, B2BInvoice
from services.b2b.models.user import UserModel as B2BUser
from services.b2c.models.user import B2CUser
from services.b2c.models.workspace import Workspace
from services.b2c.models.subscription import Subscription as B2CSubscription, Invoice as B2CInvoice

# Schemas
from services.platform.schemas.billing_schemas import (
    BillingProfileSearchResponse, 
    BillingProfileSearchItem,
    BillingProfileDetail,
    SubscriptionDetail,
    InvoiceItem,
    TrialExtendRequest,
    SubscriptionCancelRequest,
    CouponCreateRequest,
    CouponResponse
)

router = APIRouter(
    prefix="/api/platform/billing",
    tags=["Platform Billing"],
    dependencies=[Depends(verify_platform_admin)]
)

@router.get("/stats")
async def get_billing_stats(db: AsyncSession = Depends(get_db)):
    """Get high-level billing stats."""
    return {"message": "Stats placeholder"}

# ============================================================================
# UNIFIED PROFILE & SUBSCRIPTION OVERVIEW
# ============================================================================

@router.get("/profiles/search", response_model=BillingProfileSearchResponse)
async def search_billing_profiles(
    query: str,
    type: Optional[str] = Query(None, description="tenant or user"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for tenants or users to view billing details.
    """
    items = []
    from sqlalchemy import select, or_

    # Search Tenants
    if not type or type == 'tenant':
        b2b_query = select(TenantModel).where(
            or_(
                TenantModel.name.ilike(f"%{query}%"),
                TenantModel.domain.ilike(f"%{query}%")
            )
        ).limit(10)
        b2b_results = await db.execute(b2b_query)
        for t in b2b_results.scalars().all():
            items.append(BillingProfileSearchItem(
                id=t.id,
                type='tenant',
                name=t.name,
                domain=t.domain,
                status='active' if t.is_active else 'inactive'
            ))

    # Search B2C Users
    if not type or type == 'user':
        b2c_query = select(B2CUser).where(
            or_(
                B2CUser.email.ilike(f"%{query}%"),
                B2CUser.display_name.ilike(f"%{query}%")
            )
        ).limit(10)
        b2c_results = await db.execute(b2c_query)
        for u in b2c_results.scalars().all():
            items.append(BillingProfileSearchItem(
                id=u.id,
                type='user',
                name=u.display_name or 'Unknown',
                email=u.email,
                status='active' # users simpler status
            ))
            
    return BillingProfileSearchResponse(items=items)

@router.get("/profiles/{id}", response_model=BillingProfileDetail)
async def get_billing_profile(
    id: UUID, 
    type: str = Query(..., description="tenant or user"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed billing profile including subscription, invoices, etc.
    """
    from sqlalchemy import select, text
    
    # Set platform admin context to bypass RLS for all queries
    await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))

    if type == 'tenant':
        # B2B
        stmt = select(TenantModel).where(TenantModel.id == id)
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        
        # Subscriptions
        sub_stmt = select(B2BSubscription).where(B2BSubscription.tenant_id == id)
        sub_res = await db.execute(sub_stmt)
        sub = sub_res.scalar_one_or_none()
        
        # Invoices
        inv_stmt = select(B2BInvoice).where(B2BInvoice.tenant_id == id).order_by(B2BInvoice.created_at.desc())
        inv_res = await db.execute(inv_stmt)
        invoices = inv_res.scalars().all()
        
        sub_detail = None
        if sub:
            sub_detail = SubscriptionDetail(
                id=sub.id,
                status=sub.status,
                tier=sub.tier,
                amount_cents=sub.total_amount_cents or 0,
                currency=sub.currency or 'USD',
                billing_interval=sub.billing_interval,
                current_period_end=sub.current_period_end,
                trial_ends_at=sub.trial_ends_at,
                cancel_at_period_end=sub.cancel_at_period_end,
                provider=sub.provider or 'stripe',
                seat_count=sub.seat_count
            )
            
        return BillingProfileDetail(
            id=tenant.id,
            type='tenant',
            name=tenant.name,
            email=tenant.billing_email, # or fetch owner email?
            tax_id=tenant.tax_id,
            billing_address=tenant.billing_address,
            compliance_settings=getattr(tenant, 'compliance_settings', None),
            subscription=sub_detail,
            invoices=[InvoiceItem(
                id=inv.id,
                provider_invoice_id=inv.provider_invoice_id,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid or 0,
                currency=inv.currency or 'USD',
                status=inv.status or 'draft',
                created_at=inv.created_at,
                invoice_pdf_url=inv.invoice_pdf_url
            ) for inv in invoices]
        )
        
    elif type == 'user':
        # B2C
        stmt = select(B2CUser).where(B2CUser.id == id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
            
        # Get Subscription via User ID (B2C subscriptions link to user_id)
        sub_stmt = select(B2CSubscription).where(B2CSubscription.user_id == id).order_by(B2CSubscription.created_at.desc())
        sub_res = await db.execute(sub_stmt)
        sub = sub_res.scalar_one_or_none()
        
        # Invoices
        inv_stmt = select(B2CInvoice).where(B2CInvoice.user_id == id).order_by(B2CInvoice.created_at.desc())
        inv_res = await db.execute(inv_stmt)
        invoices = inv_res.scalars().all()
        
        sub_detail = None
        if sub:
            sub_detail = SubscriptionDetail(
                id=sub.id,
                status=sub.status,
                amount_cents=sub.amount_cents or 0,
                currency=sub.currency or 'USD',
                billing_interval=sub.billing_interval,
                current_period_end=sub.current_period_end,
                trial_ends_at=sub.trial_ends_at,
                cancel_at_period_end=sub.cancel_at_period_end,
                provider=sub.provider or 'stripe'
            )
            
        return BillingProfileDetail(
            id=user.id,
            type='user',
            name=user.display_name or 'Unknown',
            email=user.email,
            tax_id=user.tax_id,
            billing_address=user.billing_address,
            compliance_settings=user.compliance_settings,
            subscription=sub_detail,
            invoices=[InvoiceItem(
                id=inv.id,
                provider_invoice_id=inv.provider_invoice_id,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid or 0,
                currency=inv.currency or 'USD',
                status=inv.status or 'draft',
                created_at=inv.created_at,
                invoice_pdf_url=inv.invoice_pdf_url
            ) for inv in invoices]
        )
    else:
        raise HTTPException(400, "Invalid type")

# ============================================================================
# SUBSCRIPTION OPERATIONS
# ============================================================================

@router.post("/subscriptions/{id}/cancel")
async def cancel_subscription(
    id: UUID,
    request: SubscriptionCancelRequest,
    type: str = Query(..., description="tenant or user"),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription."""
    if type == 'tenant':
        service = B2BSubscriptionService(db)
        try:
            await service.cancel_subscription(subscription_id=id, immediate=request.immediate)
            return {"message": "Subscription cancelled"}
        except ValueError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
             raise HTTPException(500, str(e))

    elif type == 'user':
        # B2C: cancel takes 'workspace'.
        service = B2CSubscriptionService(db)
        # B2C Service requires Workspace object.
        # Find which workspace?
        # Check if subscription exists and get workspace_id
        sub = await db.get(B2CSubscription, id)
        if not sub: raise HTTPException(404, "Subscription not found")
        
        ws = await db.get(Workspace, sub.workspace_id)
        if not ws: raise HTTPException(404, "Workspace not found")

        await service.cancel_subscription(ws, immediate=request.immediate)
        return {"message": "Subscription cancelled"}
    else:
        raise HTTPException(400, "Invalid type")

@router.post("/subscriptions/{id}/extend-trial")
async def extend_trial(
    id: UUID,
    request: TrialExtendRequest,
    type: str = Query(..., description="tenant or user"),
    db: AsyncSession = Depends(get_db)
):
    """Extend trial period."""
    from datetime import timedelta, datetime, timezone
    days = request.days
    
    if type == 'tenant':
        sub = await db.get(B2BSubscription, id)
        if not sub: raise HTTPException(404, "Subscription not found")
        
        current_expiry = sub.trial_ends_at or datetime.now(timezone.utc)
        sub.trial_ends_at = current_expiry + timedelta(days=days)
        
        await db.commit()
        return {"message": f"Trial extended by {days} days", "trial_ends_at": sub.trial_ends_at}
        
    elif type == 'user':
        sub = await db.get(B2CSubscription, id)
        if not sub: raise HTTPException(404, "Subscription not found")
        
        current_expiry = sub.trial_ends_at or datetime.now(timezone.utc)
        sub.trial_ends_at = current_expiry + timedelta(days=days)
        
        await db.commit()
        return {"message": f"Trial extended by {days} days", "trial_ends_at": sub.trial_ends_at}
    else:
        raise HTTPException(400, "Invalid type")

# ============================================================================
# COUPON MANAGEMENT
# ============================================================================

@router.get("/coupons", response_model=List[CouponResponse])
async def list_coupons(
    scope: str = Query("all", enum=["b2b", "b2c", "all"]),
    db: AsyncSession = Depends(get_db)
):
    """List all coupons."""
    from services.b2b.models import Coupon as B2BCoupon
    from services.b2c.models.subscription import B2CCoupon
    from sqlalchemy import select, text
    
    # Set platform admin context to bypass RLS
    await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
    
    results = []
    
    if scope in ['b2b', 'all']:
        b2b_res = await db.execute(select(B2BCoupon).order_by(B2BCoupon.created_at.desc()))
        for c in b2b_res.scalars().all():
            results.append(CouponResponse(
                id=c.id, code=c.code, discount_type=c.discount_type,
                discount_percent=c.discount_percent, discount_amount_cents=c.discount_amount_cents,
                is_active=c.is_active or False, times_redeemed=c.times_redeemed or 0,
                provider_coupon_id=c.provider_coupon_id
            ))
            
    if scope in ['b2c', 'all']:
        b2c_res = await db.execute(select(B2CCoupon).order_by(B2CCoupon.created_at.desc()))
        for c in b2c_res.scalars().all():
            results.append(CouponResponse(
                id=c.id, code=c.code, discount_type=c.discount_type,
                discount_percent=c.discount_percent, discount_amount_cents=c.discount_amount_cents,
                is_active=c.is_active or False, times_redeemed=c.times_redeemed or 0,
                provider_coupon_id=c.provider_coupon_id
            ))
            
    return results

@router.post("/coupons", response_model=CouponResponse)
async def create_coupon(
    payload: CouponCreateRequest,
    scope: str = Query(..., enum=["b2b", "b2c"]),
    db: AsyncSession = Depends(get_db)
):
    """Create a new coupon."""
    from sqlalchemy import text
    
    # Set platform admin context to bypass RLS
    await db.execute(text("SET LOCAL app.is_platform_admin = 'true'"))
    
    if scope == 'b2b':
        service = B2BCouponService(db)
        coupon = await service.create_coupon(
            code=payload.code,
            discount_type=payload.discount_type,
            discount_percent=payload.discount_percent,
            discount_amount_cents=payload.discount_amount_cents,
            currency=payload.currency,
            max_redemptions=payload.max_redemptions,
            valid_until=payload.valid_until,
            applicable_tiers=payload.applicable_tiers,
            description=payload.description
        )
        return CouponResponse(
            id=coupon.id, code=coupon.code, discount_type=coupon.discount_type,
            discount_percent=coupon.discount_percent, discount_amount_cents=coupon.discount_amount_cents,
            is_active=coupon.is_active or False, times_redeemed=coupon.times_redeemed or 0,
             provider_coupon_id=coupon.provider_coupon_id
        )
    elif scope == 'b2c':
        service = B2CCouponService(db)
        coupon = await service.create_coupon(
            code=payload.code,
            discount_type=payload.discount_type,
            discount_percent=payload.discount_percent,
            discount_amount_cents=payload.discount_amount_cents,
            currency=payload.currency,
            max_redemptions=payload.max_redemptions,
            valid_until=payload.valid_until,
            applicable_tiers=payload.applicable_tiers,
            description=payload.description
        )
        # B2C Coupon model might default is_active=True but check mapping
        return CouponResponse(
            id=coupon.id, code=coupon.code, discount_type=coupon.discount_type,
            discount_percent=coupon.discount_percent, discount_amount_cents=coupon.discount_amount_cents,
            is_active=coupon.is_active, times_redeemed=coupon.times_redeemed or 0,
            provider_coupon_id=coupon.provider_coupon_id
        )
