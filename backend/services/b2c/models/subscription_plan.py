from sqlalchemy import Column, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from core.models.base import Base

class SubscriptionPlan(Base):
    """
    Subscription Plan configuration.
    Defines limits and features for each subscription tier.
    """
    __tablename__ = "subscription_plans"
    __table_args__ = {"schema": "b2c"}

    tier = Column(Text, primary_key=True)
    limits = Column(JSONB, nullable=False, default={})
    features = Column(JSONB, nullable=False, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SubscriptionPlan(tier={self.tier})>"
