"""
Auth Provider ORM Model for B2B Tenants

Tracks authentication providers (OIDC, SAML, Google, Microsoft, etc.) 
configured for each B2B tenant.
"""
from core.db.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, ForeignKey, text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

class AuthProvider(Base, TimestampMixin, SoftDeleteMixin):
    """
    Authentication provider model for B2B tenants.
    
    Supports multiple auth provider types per tenant:
    - OIDC (OpenID Connect)
    - SAML 2.0
    - Google
    - Microsoft Azure AD
    """
    __tablename__ = "auth_providers"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Provider identification
    provider_type = Column(String(50), nullable=False, index=True)  # 'oidc', 'saml', 'google', 'microsoft', 'azure_ad'
    provider_id = Column(String(255), nullable=False)  # Firebase provider ID (e.g., 'oidc.auth0')
    display_name = Column(String(255), nullable=True)  # Human-readable name
    
    # Configuration
    is_primary = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    config_data = Column(JSONB, nullable=True)  # Additional provider-specific config
    
    # Relationships
    # tenant = relationship("TenantModel", back_populates="auth_providers")

    @property
    def oidc_issuer_url(self):
        """Shortcut to access issuer from config_data"""
        if not self.config_data:
            return None
        return self.config_data.get('issuer_url') or self.config_data.get('issuer')

    @property
    def oidc_client_id(self):
        """Shortcut to access client_id from config_data"""
        if not self.config_data:
            return None
        return self.config_data.get('client_id')

    @property
    def oidc_client_id_mobile(self):
        """Shortcut to access mobile_client_id from config_data"""
        if not self.config_data:
            return None
        return self.config_data.get('mobile_client_id')
    
    def __repr__(self):
        return f"<AuthProvider(id={self.id}, tenant_id={self.tenant_id}, type={self.provider_type}, provider_id={self.provider_id})>"
