from sqlalchemy import Column, Text, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from core.models.base import Base

class SubscriptionPlan(Base):
    """
    Subscription Plan configuration.
    Defines limits and features for each subscription tier.
    """
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "b2c"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tier_key = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    price_monthly = Column(Integer)
    price_yearly = Column(Integer)
    
    provider_config = Column(JSONB, default={})
    limits = Column(JSONB, nullable=False, default={})
    features = Column(JSONB, nullable=False, default={})
    
    effective_from = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SubscriptionPlan(tier_key={self.tier_key}, name={self.name})>"
