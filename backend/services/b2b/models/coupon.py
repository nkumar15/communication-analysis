"""
B2B Coupon Models
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP, ARRAY, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.models.base import Base

class B2BCoupon(Base):
    __tablename__ = "coupons"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Coupon Details
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    provider_coupon_id = Column(String(255))
    
    # Discount
    discount_type = Column(String(20), nullable=False) # 'percentage', 'fixed_amount'
    discount_percent = Column(Integer)
    discount_amount_cents = Column(Integer)
    currency = Column(String(3), default="USD")
    
    # Usage Limits
    max_redemptions = Column(Integer)
    times_redeemed = Column(Integer, default=0)
    
    # Validity
    valid_from = Column(TIMESTAMP(timezone=True), server_default=func.now())
    valid_until = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Applicable Tiers
    applicable_tiers = Column(ARRAY(Text)) # e.g. ['starter', 'professional']
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    redemptions = relationship("B2BCouponRedemption", back_populates="coupon")


class B2BCouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("b2b.coupons.id", ondelete="CASCADE"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"))
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2b.subscriptions.id", ondelete="SET NULL"))
    
    # Discount Applied
    discount_amount_cents = Column(Integer)
    
    # Metadata
    redeemed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    redeemed_by = Column(UUID(as_uuid=True)) # User ID who redeemed
    
    # Relationships
    coupon = relationship("B2BCoupon", back_populates="redemptions")
    tenant = relationship("TenantModel", back_populates="coupon_redemptions")
