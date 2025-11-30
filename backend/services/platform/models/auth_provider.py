"""
Auth Provider ORM Model for Platform

Tracks authentication providers configured for platform administrators.
"""
from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, Boolean, ForeignKey, text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

class PlatformAuthProvider(Base, TimestampMixin):
    """
    Authentication provider model for platform administrators.
    
    Supports multiple auth provider types:
    - OIDC (OpenID Connect)
    - SAML 2.0
    - Google
    - Microsoft Azure AD
    """
    __tablename__ = "auth_providers"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Provider identification
    provider_type = Column(String(50), nullable=False, index=True)  # 'oidc', 'saml', 'google', 'microsoft', 'azure_ad'
    provider_id = Column(String(255), nullable=False)  # Firebase provider ID (e.g., 'oidc.auth0')
    display_name = Column(String(255), nullable=True)  # Human-readable name
    
    # Configuration
    is_primary = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    config_data = Column(JSONB, nullable=True)  # Additional provider-specific config
    
    # Relationships
    # platform_tenant = relationship("PlatformTenant", back_populates="auth_providers")
    
    def __repr__(self):
        return f"<PlatformAuthProvider(id={self.id}, platform_tenant_id={self.platform_tenant_id}, type={self.provider_type}, provider_id={self.provider_id})>"
