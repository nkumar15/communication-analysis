"""
Async Coupon Service

Business logic for coupon validation, redemption, and discount calculation.
Uses async SQLAlchemy patterns for compatibility with AsyncSession.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, timezone
import logging

from services.b2c.models.subscription import B2CCoupon as Coupon, B2CCouponRedemption as CouponRedemption, Subscription
from services.b2c.models.user import B2CUser
from core.payment import PaymentProviderFactory
from core.config import settings

logger = logging.getLogger(__name__)


def get_user_id(user: Union[B2CUser, Dict[str, Any]]) -> Any:
    """Extract user ID from either a B2CUser object or a dict."""
    if isinstance(user, dict):
        return user.get('id')
    return user.id


# ============================================================================
# Exceptions
# ============================================================================

class CouponError(Exception):
    """Base exception for coupon-related errors."""
    pass


class CouponNotFoundError(CouponError):
    """Coupon code does not exist."""
    pass


class CouponExpiredError(CouponError):
    """Coupon has expired."""
    pass


class CouponInactiveError(CouponError):
    """Coupon is not active."""
    pass


class CouponMaxRedemptionsError(CouponError):
    """Coupon has reached maximum redemptions."""
    pass


class CouponAlreadyRedeemedError(CouponError):
    """User has already redeemed this coupon."""
    pass


class CouponNotApplicableError(CouponError):
    """Coupon is not applicable to this tier."""
    pass


# ============================================================================
# Async Coupon Service
# ============================================================================

class CouponService:
    """
    Async service for managing coupons, discounts, and promotional offers.
    All database operations use async SQLAlchemy patterns.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Initialize Stripe provider (Defaulting to Stripe for coupon management for now)
        self.provider = PaymentProviderFactory.create(
            'stripe',
            config={
                'secret_key': settings.stripe_secret_key,
                'webhook_secret': settings.stripe_webhook_secret,
            }
        )
    
    async def validate_coupon(
        self,
        code: str,
        user: B2CUser,
        tier: Optional[str] = None
    ) -> Coupon:
        """
        Validate a coupon code.
        
        Args:
            code: Coupon code
            user: User attempting to use coupon
            tier: Subscription tier (for applicability check)
            
        Returns:
            Coupon object if valid
            
        Raises:
            CouponNotFoundError: Code doesn't exist
            CouponExpiredError: Coupon expired
            CouponInactiveError: Coupon not active
            CouponMaxRedemptionsError: Max redemptions reached
            CouponAlreadyRedeemedError: User already redeemed
            CouponNotApplicableError: Not applicable to tier
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
        
        # Check if user already redeemed
        user_id = get_user_id(user)
        result = await self.db.execute(
            select(CouponRedemption).where(
                and_(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.user_id == user_id
                )
            )
        )
        existing_redemption = result.scalar_one_or_none()
        
        if existing_redemption:
            raise CouponAlreadyRedeemedError(f"You have already used coupon '{code}'")
        
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
        
        Args:
            coupon: Coupon object
            amount_cents: Original amount in cents
            currency: Currency code
            
        Returns:
            Discount amount in cents
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
        user: B2CUser,
        subscription: Subscription,
        discount_amount_cents: int
    ) -> CouponRedemption:
        """
        Record a coupon redemption.
        
        Args:
            coupon: Coupon being redeemed
            user: User redeeming the coupon
            subscription: Subscription the coupon is applied to
            discount_amount_cents: Actual discount amount applied
            
        Returns:
            CouponRedemption object
        """
        # Create redemption record
        user_id = get_user_id(user)
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            user_id=user_id,
            subscription_id=subscription.id,
            discount_amount_cents=discount_amount_cents
        )
        self.db.add(redemption)
        
        # Increment times_redeemed
        coupon.times_redeemed += 1
        
        await self.db.flush()
        
        logger.info(
            f"Coupon redeemed: {coupon.code} by user {user_id}, "
            f"discount: {discount_amount_cents/100:.2f} {subscription.currency}"
        )
        
        return redemption
    
    async def get_available_coupons(
        self,
        tier: Optional[str] = None,
        limit: int = 10
    ) -> List[Coupon]:
        """
        Get list of active promotional coupons.
        
        Args:
            tier: Filter by applicable tier
            limit: Maximum number of coupons to return
            
        Returns:
            List of active coupons
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
    
    async def get_user_redemptions(
        self,
        user: B2CUser,
        limit: int = 10
    ) -> List[CouponRedemption]:
        """
        Get coupon redemptions for a user.
        
        Args:
            user: User to get redemptions for
            limit: Maximum number to return
            
        Returns:
            List of CouponRedemption objects
        """
        result = await self.db.execute(
            select(CouponRedemption)
            .where(CouponRedemption.user_id == get_user_id(user))
            .order_by(CouponRedemption.redeemed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_coupon_by_id(self, coupon_id) -> Optional[Coupon]:
        """Get coupon by ID."""
        result = await self.db.execute(
            select(Coupon).where(Coupon.id == coupon_id)
        )
        return result.scalar_one_or_none()
    
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
        """
        if discount_type == 'percentage' and discount_percent is None:
            raise ValueError("discount_percent required for percentage discount")
        
        if discount_type == 'fixed_amount' and discount_amount_cents is None:
            raise ValueError("discount_amount_cents required for fixed amount discount")
        
        coupon = Coupon(
            code=code.upper(),
            discount_type=discount_type,
            discount_percent=discount_percent,
            discount_amount_cents=discount_amount_cents,
            currency=currency,
            max_redemptions=max_redemptions,
            valid_until=valid_until,
            applicable_tiers=applicable_tiers,
            description=description
        )
        
        # 1. Create Stripe Coupon (optional in test mode)
        try:
            stripe_data = await self.provider.create_coupon(
                duration='forever',
                name=f"{code} ({description or 'B2C Coupon'})",
                percent_off=float(discount_percent) if discount_percent else None,
                amount_off=discount_amount_cents,
                currency=currency.lower() if discount_amount_cents else None,
                max_redemptions=max_redemptions,
                redeem_by=int(valid_until.timestamp()) if valid_until else None,
                metadata={'code': code}
            )
            coupon.provider_coupon_id = stripe_data['provider_coupon_id']
            logger.info(f"Created Stripe coupon: {coupon.provider_coupon_id}")
        except Exception as e:
            logger.error(f"Failed to create Stripe coupon: {e}")
            # In test mode or when Stripe is unavailable, use a test ID
            import os
            if os.getenv('TESTING') == 'true':
                coupon.provider_coupon_id = f"test_coupon_{code.lower()}"
                logger.warning(f"Using test provider_coupon_id: {coupon.provider_coupon_id}")
            else:
                raise ValueError(f"Failed to create provider coupon: {str(e)}")
        
        self.db.add(coupon)
        await self.db.flush()
        
        logger.info(f"Coupon created: {coupon.code}")
        
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
        
        logger.info(f"Coupon deactivated: {coupon.code}")
        
        return coupon
