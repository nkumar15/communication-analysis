"""
Coupon Service

Business logic for coupon validation, redemption, and discount calculation.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from services.b2c.models.subscription import Coupon, CouponRedemption, Subscription
from services.b2c.models.user import B2CUser

logger = logging.getLogger(__name__)


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
# Coupon Service
# ============================================================================

class CouponService:
    """
    Service for managing coupons, discounts, and promotional offers.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_coupon(
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
        coupon = self.db.query(Coupon).filter(
            Coupon.code == code.upper()
        ).first()
        
        if not coupon:
            raise CouponNotFoundError(f"Coupon code '{code}' not found")
        
        # Check if active
        if not coupon.is_active:
            raise CouponInactiveError(f"Coupon '{code}' is not active")
        
        # Check expiry
        now = datetime.now()
        if coupon.valid_from and now < coupon.valid_from:
            raise CouponExpiredError(f"Coupon '{code}' is not yet valid")
        
        if coupon.valid_until and now > coupon.valid_until:
            raise CouponExpiredError(f"Coupon '{code}' has expired")
        
        # Check max redemptions
        if coupon.max_redemptions is not None:
            if coupon.times_redeemed >= coupon.max_redemptions:
                raise CouponMaxRedemptionsError(f"Coupon '{code}' has reached maximum redemptions")
        
        # Check if user already redeemed
        existing_redemption = self.db.query(CouponRedemption).filter(
            and_(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.user_id == user.id
            )
        ).first()
        
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
            # Only apply if currency matches
            if coupon.currency.upper() == currency.upper():
                discount_cents = coupon.discount_amount_cents
            else:
                logger.warning(
                    f"Coupon currency mismatch: {coupon.currency} vs {currency}"
                )
                discount_cents = 0
        else:
            discount_cents = 0
        
        # Ensure discount doesn't exceed total
        return min(discount_cents, amount_cents)
    
    def redeem_coupon(
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
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            user_id=user.id,
            subscription_id=subscription.id,
            discount_amount_cents=discount_amount_cents
        )
        self.db.add(redemption)
        
        # Increment times_redeemed
        coupon.times_redeemed += 1
        
        self.db.commit()
        self.db.refresh(redemption)
        
        logger.info(
            f"Coupon redeemed: {coupon.code} by user {user.id}, "
            f"discount: {discount_amount_cents/100:.2f} {subscription.currency}"
        )
        
        return redemption
    
    def get_available_coupons(
        self,
        tier: Optional[str] = None,
        limit: int = 10
    ) -> list[Coupon]:
        """
        Get list of active promotional coupons.
        
        Note: In production, you might want to limit this to specific
        promotional campaigns rather than exposing all active coupons.
        
        Args:
            tier: Filter by applicable tier
            limit: Maximum number of coupons to return
            
        Returns:
            List of active coupons
        """
        now = datetime.now()
        
        query = self.db.query(Coupon).filter(
            Coupon.is_active == True,
            Coupon.valid_from <= now
        )
        
        # Filter by expiry
        query = query.filter(
            (Coupon.valid_until.is_(None)) | (Coupon.valid_until > now)
        )
        
        # Filter by tier if specified
        if tier:
            query = query.filter(
                (Coupon.applicable_tiers.is_(None)) | 
                (Coupon.applicable_tiers.contains([tier]))
            )
        
        # Filter by redemptions
        query = query.filter(
            (Coupon.max_redemptions.is_(None)) |
            (Coupon.times_redeemed < Coupon.max_redemptions)
        )
        
        return query.limit(limit).all()
    
    def get_user_redemptions(
        self,
        user: B2CUser,
        limit: int = 10
    ) -> list[CouponRedemption]:
        """
        Get coupon redemptions for a user.
        
        Args:
            user: User to get redemptions for
            limit: Maximum number to return
            
        Returns:
            List of CouponRedemption objects
        """
        return self.db.query(CouponRedemption).filter(
            CouponRedemption.user_id == user.id
        ).order_by(
            CouponRedemption.redeemed_at.desc()
        ).limit(limit).all()
    
    def create_coupon(
        self,
        code: str,
        discount_type: str,
        discount_percent: Optional[int] = None,
        discount_amount_cents: Optional[int] = None,
        currency: str = 'USD',
        max_redemptions: Optional[int] = None,
        valid_until: Optional[datetime] = None,
        applicable_tiers: Optional[list[str]] = None,
        description: Optional[str] = None
    ) -> Coupon:
        """
        Create a new coupon (admin function).
        
        Args:
            code: Unique coupon code
            discount_type: 'percentage' or 'fixed_amount'
            discount_percent: Discount percentage (0-100)
            discount_amount_cents: Fixed discount amount in cents
            currency: Currency for fixed amount
            max_redemptions: Maximum number of redemptions
            valid_until: Expiry date
            applicable_tiers: List of applicable tiers
            description: Coupon description
            
        Returns:
            Created Coupon object
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
        
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        
        logger.info(f"Coupon created: {coupon.code}")
        
        return coupon
    
    def deactivate_coupon(self, coupon_id: str) -> Coupon:
        """
        Deactivate a coupon (admin function).
        
        Args:
            coupon_id: Coupon ID to deactivate
            
        Returns:
            Updated Coupon object
        """
        coupon = self.db.query(Coupon).filter(Coupon.id == coupon_id).first()
        
        if not coupon:
            raise CouponNotFoundError(f"Coupon {coupon_id} not found")
        
        coupon.is_active = False
        self.db.commit()
        self.db.refresh(coupon)
        
        logger.info(f"Coupon deactivated: {coupon.code}")
        
        return coupon
