from core.models.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class TenantModel(Base, TimestampMixin, SoftDeleteMixin):
    """Customer Tenant ORM model"""
    __tablename__ = "tenants"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    logo_url = Column(String(500), nullable=True)  # Added for branding
    firebase_tenant_id = Column(String(255), unique=True, nullable=False)
    
    # Activation fields
    activation_token = Column(String(64), unique=True, nullable=True, index=True)
    activation_status = Column(String(20), default='pending', nullable=False, index=True)
    activation_expires_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    activated_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=True)
    activation_started_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships (billing-related)
    subscription = relationship("B2BSubscription", back_populates="tenant", uselist=False)
    invoices = relationship("B2BInvoice", back_populates="tenant")
    subscription_events = relationship("B2BSubscriptionEvent", back_populates="tenant")
    payment_mode_requests = relationship("PaymentModeRequest", back_populates="tenant")

