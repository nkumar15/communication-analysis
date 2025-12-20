from sqlalchemy import Column, String, Integer, JSON, TIMESTAMP, ForeignKey, func, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.models.base import Base

class B2BSubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tier_key = Column(String(50), nullable=False, index=True) # e.g. 'starter', 'professional' (logical ID)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Pricing Configuration
    base_price_monthly = Column(Integer, default=0) # cents
    base_price_yearly = Column(Integer, default=0) # cents
    per_seat_price_monthly = Column(Integer, default=0) # cents
    per_seat_price_yearly = Column(Integer, default=0) # cents
    
    # Quotas & Features
    limits = Column(JSONB, default=dict) # { 'projects': 5, 'storage_gb': 10 }
    features = Column(JSONB, default=dict) # { 'sso': true, 'audit_logs': false }
    
    # Provider Mapping (e.g. Stripe Price IDs)
    provider_config = Column(JSONB, default=dict) # { 'stripe': { 'monthly_price_id': ... } }
    
    # UI Flags
    contact_required = Column(Boolean, default=False) # If true, show "Contact Us" instead of price
    
    # Scheduling & Versioning
    effective_from = Column(TIMESTAMP(timezone=True), server_default=func.now())
    archived_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
