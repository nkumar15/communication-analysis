"""
Async Coupon Service for B2B

Business logic for coupon validation, redemption, and discount calculation.
Uses async SQLAlchemy patterns.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, timezone
import logging
from uuid import UUID

from modules.b2b.models import (
    B2BCoupon as Coupon, 
    B2BCouponRedemption as CouponRedemption, 
    B2BSubscription, 
    TenantModel
)
from infrastructure.payment import PaymentProviderFactory
from core.config import settings

logger = logging.getLogger(__name__)


# Exceptions remain same because they are local classes not models

class B2BCouponService:
    """
    Async service for managing B2B coupons.
    """


    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize Stripe provider
        self.provider = PaymentProviderFactory.create(
            'stripe',
            config={
                'secret_key': settings.stripe_b2b_secret_key,
                'webhook_secret': settings.stripe_b2b_webhook_secret,
            }
        )
    
    async def validate_coupon(
        self,
        code: str,
        tenant_id: UUID,
        tier: Optional[str] = None
    ) -> Coupon:
        """
        Validate a coupon code for a tenant.
        
        Args:
            code: Coupon code
            tenant_id: Tenant attempting to use coupon
            tier: Subscription tier (for applicability check)
            
        Returns:
            Coupon object if valid
        """
        # Find coupon
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code.upper())
        )
        coupon = result.scalar_one_or_none()
        
        if not coupon:
            raise CouponNotFoundError(f"Coupon code '{code}' not found")
        
        # Check if active
        if not coupon.is_active:
            raise CouponInactiveError(f"Coupon '{code}' is not active")
        
        # Check expiry
        now = datetime.now(timezone.utc)
        if coupon.valid_from and now < coupon.valid_from:
            raise CouponExpiredError(f"Coupon '{code}' is not yet valid")
        
        if coupon.valid_until and now > coupon.valid_until:
            raise CouponExpiredError(f"Coupon '{code}' has expired")
        
        # Check max redemptions
        if coupon.max_redemptions is not None:
            if coupon.times_redeemed >= coupon.max_redemptions:
                raise CouponMaxRedemptionsError(f"Coupon '{code}' has reached maximum redemptions")
        
        # Check if tenant already redeemed
        result = await self.db.execute(
            select(CouponRedemption).where(
                and_(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.tenant_id == tenant_id
                )
            )
        )
        existing_redemption = result.scalar_one_or_none()
        
        if existing_redemption:
            raise CouponAlreadyRedeemedError(f"Tenant has already utilized coupon '{code}'")
        
        # Check tier applicability
        if tier and coupon.applicable_tiers:
            if tier not in coupon.applicable_tiers:
                raise CouponNotApplicableError(
                    f"Coupon '{code}' is not applicable to the {tier} tier. "
                    f"Valid for: {', '.join(coupon.applicable_tiers)}"
                )
        
        return coupon
    
    def calculate_discount(
        self,
        coupon: Coupon,
        amount_cents: int,
        currency: str = 'USD'
    ) -> int:
        """
        Calculate discount amount.
        """
        if coupon.discount_type == 'percentage':
            discount_cents = int((amount_cents * coupon.discount_percent) / 100)
        elif coupon.discount_type == 'fixed_amount':
            if coupon.currency and coupon.currency.upper() == currency.upper():
                discount_cents = coupon.discount_amount_cents or 0
            else:
                logger.warning(
                    f"Coupon currency mismatch: {coupon.currency} vs {currency}"
                )
                discount_cents = 0
        else:
            discount_cents = 0
        
        return min(discount_cents, amount_cents)
    
    async def redeem_coupon(
        self,
        coupon: Coupon,
        tenant_id: UUID,
        subscription: B2BSubscription,
        discount_amount_cents: int,
        redeemed_by: Optional[UUID] = None
    ) -> CouponRedemption:
        """
        Record a coupon redemption.
        """
        # Create redemption record
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            tenant_id=tenant_id,
            subscription_id=subscription.id,
            discount_amount_cents=discount_amount_cents,
            redeemed_by=redeemed_by
        )
        self.db.add(redemption)
        
        # Increment times_redeemed
        coupon.times_redeemed += 1
        
        await self.db.flush()
        
        logger.info(
            f"Coupon redeemed: {coupon.code} by tenant {tenant_id}, "
            f"discount: {discount_amount_cents/100:.2f}"
        )
        
        return redemption
    
    async def get_available_coupons(
        self,
        tier: Optional[str] = None,
        limit: int = 10
    ) -> List[Coupon]:
        """
        Get list of active promotional coupons.
        """
        now = datetime.now(timezone.utc)
        
        # Build base query
        stmt = select(Coupon).where(
            Coupon.is_active == True
        ).where(
            (Coupon.valid_from.is_(None)) | (Coupon.valid_from <= now)
        ).where(
            (Coupon.valid_until.is_(None)) | (Coupon.valid_until > now)
        ).where(
            (Coupon.max_redemptions.is_(None)) |
            (Coupon.times_redeemed < Coupon.max_redemptions)
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_percent: Optional[int] = None,
        discount_amount_cents: Optional[int] = None,
        currency: str = 'USD',
        max_redemptions: Optional[int] = None,
        valid_until: Optional[datetime] = None,
        applicable_tiers: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Coupon:
        """
        Create a new coupon (admin function).
        Creates in Stripe first, then DB.
        """
        if discount_type == 'percentage' and discount_percent is None:
            raise ValueError("discount_percent required for percentage discount")
        
        if discount_type == 'fixed_amount' and discount_amount_cents is None:
            raise ValueError("discount_amount_cents required for fixed amount discount")
            
        # 1. Create Stripe Coupon
        # We try to use the code as the ID for simplicity
        provider_coupon_id = None
        try:
            stripe_data = await self.provider.create_coupon(
                duration='forever', # Defaulting to forever for now, or 'once' if redemptions=1? 
                                  # Usually admins want 'repeating' or 'forever' for subscription discounts.
                                  # Let's assume 'repeating' if valid_until is set? Or just 'forever'.
                                  # Better: Add 'duration' to create_coupon args? Default 'forever'.
                name=f"{code} ({description or 'B2B Coupon'})",
                percent_off=float(discount_percent) if discount_percent else None,
                amount_off=discount_amount_cents,
                currency=currency.lower() if discount_amount_cents else None,
                max_redemptions=max_redemptions,
                redeem_by=int(valid_until.timestamp()) if valid_until else None,
                metadata={'code': code}
            )
            provider_coupon_id = stripe_data['provider_coupon_id']
            logger.info(f"Created Stripe coupon: {provider_coupon_id}")
        except Exception as e:
            logger.error(f"Failed to create Stripe coupon: {e}")
            # If it already exists (likely if we rely on IDs), we might want to fail or proceed?
            # Stripe create_coupon without ID generates one "Z4x..."
            # For "Promotion Code" flow we need a Coupon.
            # But earlier I decided to use "discounts=[{'coupon': ID}]".
            # So provider_coupon_id is crucial.
            # If failed, we should probably abort creation.
            raise ValueError(f"Failed to create provider coupon: {str(e)}")

        # 2. Save to DB
        coupon = Coupon(
            code=code.upper(),
            discount_type=discount_type,
            discount_percent=discount_percent,
            discount_amount_cents=discount_amount_cents,
            currency=currency,
            max_redemptions=max_redemptions,
            valid_until=valid_until,
            applicable_tiers=applicable_tiers,
            description=description,
            provider_coupon_id=provider_coupon_id
        )
        
        self.db.add(coupon)
        await self.db.flush()
        
        logger.info(f"B2B Coupon created: {coupon.code}")
        
        return coupon
    
    async def deactivate_coupon(self, coupon_id: str) -> Coupon:
        """
        Deactivate a coupon (admin function).
        """
        result = await self.db.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        coupon = result.scalar_one_or_none()
        
        if not coupon:
            raise CouponNotFoundError(f"Coupon {coupon_id} not found")
        
        coupon.is_active = False
        await self.db.flush()
        
        return coupon
