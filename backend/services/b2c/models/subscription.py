"""
Subscription model for B2C billing
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP, ARRAY, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "b2c"}

    from services.b2c.models.subscription_plan import SubscriptionPlan

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("b2c.workspaces.id", ondelete="CASCADE"), unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("b2c.users.id", ondelete="CASCADE"))
    
    # Plan Link
    plan_id = Column(UUID(as_uuid=True), ForeignKey("b2c.subscription_plans.id"))
    
    # Provider Info
    provider = Column(String(50), nullable=False, default="stripe")
    provider_customer_id = Column(String(255))
    provider_subscription_id = Column(String(255), unique=True)
    
    # Plan Details (Derived/Override)
    billing_interval = Column(String(20), default="monthly")
    
    # Status
    status = Column(String(50), default="active")
    trial_ends_at = Column(TIMESTAMP(timezone=True))
    current_period_start = Column(TIMESTAMP(timezone=True))
    current_period_end = Column(TIMESTAMP(timezone=True))
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(TIMESTAMP(timezone=True))
    
    # Pricing
    amount_cents = Column(Integer, default=0)
    currency = Column(String(3), default="USD")
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="subscription")
    user = relationship("B2CUser", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    events = relationship("SubscriptionEvent", back_populates="subscription")
    plan = relationship("SubscriptionPlan")


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), ForeignKey("b2c.users.id", ondelete="CASCADE"))
    
    # Provider Info
    provider = Column(String(50), nullable=False, default="stripe")
    provider_payment_method_id = Column(String(255), unique=True)
    provider_customer_id = Column(String(255))
    
    # Card Details
    type = Column(String(50))
    card_brand = Column(String(50))
    card_last4 = Column(String(4))
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)
    
    # Metadata
    is_default = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("B2CUser", back_populates="payment_methods")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2c.subscriptions.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("b2c.users.id", ondelete="CASCADE"))
    
    # Provider Info
    provider = Column(String(50), nullable=False, default="stripe")
    provider_invoice_id = Column(String(255), unique=True)
    
    # Invoice Details
    amount_due = Column(Integer, nullable=False)
    amount_paid = Column(Integer, default=0)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="draft")
    
    # URLs
    invoice_pdf_url = Column(Text)
    hosted_invoice_url = Column(Text)
    
    # Dates
    invoice_date = Column(TIMESTAMP(timezone=True))
    due_date = Column(TIMESTAMP(timezone=True))
    paid_at = Column(TIMESTAMP(timezone=True))
    billing_period_start = Column(TIMESTAMP(timezone=True))
    billing_period_end = Column(TIMESTAMP(timezone=True))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="invoices")
    user = relationship("B2CUser", back_populates="invoices")


class SubscriptionEvent(Base):
    __tablename__ = "subscription_events"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2c.subscriptions.id", ondelete="CASCADE"))
    
    # Event Details
    event_type = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False, default="stripe")
    provider_event_id = Column(String(255))
    
    # Payload
    payload = Column(JSONB)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("Subscription", back_populates="events")


class B2CCoupon(Base):
    __tablename__ = "coupons"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    
    # Coupon Details
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    provider_coupon_id = Column(String(255))
    
    # Discount
    discount_type = Column(String(20), nullable=False)
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
    applicable_tiers = Column(ARRAY(Text))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    redemptions = relationship("B2CCouponRedemption", back_populates="coupon")


class B2CCouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    coupon_id = Column(UUID(as_uuid=True), ForeignKey("b2c.coupons.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("b2c.users.id", ondelete="CASCADE"))
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2c.subscriptions.id", ondelete="SET NULL"))
    
    # Discount Applied
    discount_amount_cents = Column(Integer)
    
    # Timestamps
    redeemed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    coupon = relationship("B2CCoupon", back_populates="redemptions")
    user = relationship("B2CUser", back_populates="coupon_redemptions")

# Backward compatibility aliases
Coupon = B2CCoupon
CouponRedemption = B2CCouponRedemption
