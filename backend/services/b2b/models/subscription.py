"""
B2B Billing Models

SQLAlchemy ORM models for B2B subscription management, invoices, and payment mode requests.
"""
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, TIMESTAMP, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.models.base import Base


# ============================================================================
# ENUMS
# ============================================================================

class SubscriptionTier(str, PyEnum):
    """B2B subscription tiers"""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PaymentMode(str, PyEnum):
    """Payment modes for B2B subscriptions"""
    CARD = "card"  # Stripe card payment
    INVOICE = "invoice"  # Invoice/wire transfer


class SubscriptionStatus(str, PyEnum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class InvoiceStatus(str, PyEnum):
    """Invoice lifecycle statuses"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"
    REFUNDED = "refunded"


class PaymentModeRequestStatus(str, PyEnum):
    """Payment mode change request statuses"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"  # Approved but not yet applied (waiting for billing period)
    APPLIED = "applied"  # Change has been applied to subscription


# ============================================================================
# SUBSCRIPTION MODEL
# ============================================================================

class B2BSubscription(Base):
    """B2B Subscription with base + per-seat pricing model"""
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Subscription Details
    tier = Column(String(50), nullable=False, default="starter")
    
    # Link to Plan (Database Driven)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('b2b.subscription_plans.id'), nullable=True)
    
    payment_mode = Column(String(20), nullable=False, default="card")
    status = Column(String(50), default="active")
    
    # Pricing (Base + Per-Seat Model)
    seat_count = Column(Integer, nullable=False, default=1)
    base_price_cents = Column(Integer, nullable=False, default=0)
    per_seat_price_cents = Column(Integer, nullable=False, default=0)
    total_amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), default="USD")
    billing_interval = Column(String(20), default="monthly")
    
    # Billing Cycle
    current_period_start = Column(TIMESTAMP(timezone=True))
    current_period_end = Column(TIMESTAMP(timezone=True))
    trial_ends_at = Column(TIMESTAMP(timezone=True))
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(TIMESTAMP(timezone=True))
    
    # Stripe Provider Info (for card mode)
    provider = Column(String(50), nullable=False, default="stripe")
    provider_customer_id = Column(String(255))
    provider_subscription_id = Column(String(255), unique=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("TenantModel", back_populates="subscription")
    invoices = relationship("B2BInvoice", back_populates="subscription")
    events = relationship("B2BSubscriptionEvent", back_populates="subscription")
    payment_mode_requests = relationship("PaymentModeRequest", back_populates="subscription")


# ============================================================================
# INVOICE MODEL
# ============================================================================

class B2BInvoice(Base):
    """B2B Invoices for both card and invoice payment modes"""
    __tablename__ = "invoices"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2b.subscriptions.id", ondelete="SET NULL"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Invoice Identification
    invoice_number = Column(String(50), unique=True, nullable=False)
    
    # Provider Info (for card mode invoices from Stripe)
    provider = Column(String(50), default="manual")
    provider_invoice_id = Column(String(255), unique=True)
    
    # Invoice Details
    status = Column(String(50), default="draft")
    amount_due = Column(Integer, nullable=False)
    amount_paid = Column(Integer, default=0)
    currency = Column(String(3), default="USD")
    
    # Seat Snapshot (for audit trail)
    seat_count_snapshot = Column(Integer, nullable=False)
    base_price_snapshot_cents = Column(Integer, nullable=False)
    per_seat_price_snapshot_cents = Column(Integer, nullable=False)
    
    # Billing Period
    billing_period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    billing_period_end = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Dates
    invoice_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    due_date = Column(TIMESTAMP(timezone=True))
    paid_at = Column(TIMESTAMP(timezone=True))
    
    # URLs (for Stripe invoices)
    invoice_pdf_url = Column(Text)
    hosted_invoice_url = Column(Text)
    
    # Approval Workflow (for manual invoices)
    approved_by = Column(UUID(as_uuid=True))  # Platform admin user ID
    approved_at = Column(TIMESTAMP(timezone=True))
    
    # Payment Confirmation (for manual invoices)
    marked_paid_by = Column(UUID(as_uuid=True))  # Platform admin user ID
    payment_notes = Column(Text)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    subscription = relationship("B2BSubscription", back_populates="invoices")
    tenant = relationship("TenantModel", back_populates="invoices")


# ============================================================================
# SUBSCRIPTION EVENT MODEL (Audit Trail)
# ============================================================================

class B2BSubscriptionEvent(Base):
    """Audit trail for all subscription-related events"""
    __tablename__ = "subscription_events"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2b.subscriptions.id", ondelete="CASCADE"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Event Details
    event_type = Column(String(100), nullable=False)
    provider = Column(String(50), default="system")
    provider_event_id = Column(String(255))
    
    # Event Data
    payload = Column(JSONB)
    
    # Actor
    triggered_by = Column(UUID(as_uuid=True))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    subscription = relationship("B2BSubscription", back_populates="events")
    tenant = relationship("TenantModel", back_populates="subscription_events")


# ============================================================================
# PAYMENT MODE REQUEST MODEL (Approval Workflow)
# ============================================================================

class PaymentModeRequest(Base):
    """Approval workflow for payment mode changes (card ↔ invoice)"""
    __tablename__ = "payment_mode_requests"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("b2b.subscriptions.id", ondelete="CASCADE"))
    
    # Request Details
    current_mode = Column(String(20), nullable=False)
    requested_mode = Column(String(20), nullable=False)
    status = Column(String(50), default="pending")
    
    # Requester
    user_id = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'))
    
    # Link to Plan (Database Driven)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('b2b.subscription_plans.id'), nullable=True)
    
    # Status & Billing(Text)
    
    # Reviewer
    reviewed_by = Column(UUID(as_uuid=True))  # Platform admin user ID
    reviewed_at = Column(TIMESTAMP(timezone=True))
    admin_notes = Column(Text)
    
    # Scheduling (no mid-cycle changes)
    effective_date = Column(TIMESTAMP(timezone=True))
    applied_at = Column(TIMESTAMP(timezone=True))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("TenantModel", back_populates="payment_mode_requests")
    subscription = relationship("B2BSubscription", back_populates="payment_mode_requests")
