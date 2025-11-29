from core.models.base import Base
from sqlalchemy import Column, String, ForeignKey, text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

class PlatformAuditLog(Base):
    """
    Audit log for platform user actions.
    
    Tracks all actions performed by platform users for security,
    compliance, and debugging.
    """
    __tablename__ = "platform_audit_log"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_users.id', ondelete='SET NULL'), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Denormalized
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
