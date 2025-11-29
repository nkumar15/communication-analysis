from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID

class PlatformTenant(Base, TimestampMixin):
    """
    Platform Tenant model - Represents THE platform itself.
    
    This is a singleton table (only one row) representing the SaaS platform
    as an entity. Completely separate from customer tenants.
    """
    __tablename__ = "platform_tenant"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), nullable=False, default='SaaS Platform')
    firebase_tenant_id = Column(String(255), unique=True, nullable=False)
    oidc_provider_id = Column(String(255), nullable=True)
    
    # Configuration
    email_domain = Column(String(255), nullable=True)
    support_email = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
