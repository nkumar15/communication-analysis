"""
Activation Schemas

Schemas for tenant activation workflow.
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID


class ActivationValidationResponse(BaseModel):
    """Response for activation token validation"""
    tenant_id: UUID
    tenant_name: str
    domain: str
    admin_email: EmailStr
    expires_at: datetime


class ActivationCompleteRequest(BaseModel):
    """Request to complete activation"""
    activation_token: str


class ActivationTenantInfoResponse(BaseModel):
    """Response with tenant SSO configuration"""
    tenant_id: UUID
    tenant_name: str
    firebase_tenant_id: str
    oidc_provider_id: str | None
    mobile_oidc_provider_id: str | None = None
    provider_type: str | None = 'oidc'


class ActivationStatusResponse(BaseModel):
    """Response for activation status check"""
    status: str  # 'ready', 'pending', 'invalid'
    message: str
    user_created: bool = False


class SSOSetupRequest(BaseModel):
    """Request to configure SSO during activation"""
    activation_token: str
    provider_type: str
    provider_config: dict  # Generic fields like client_id, client_secret, issuer, etc.
    # We might map these to specific fields later or keep generic.
    # For now, let's keep it generic to match how onboard_tenant worked.
    
    # Specific fields for ease of use/validation if needed
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_issuer: str | None = None
    saml_entity_id: str | None = None
    saml_sso_url: str | None = None


class SSOSetupResponse(BaseModel):
    """Response after setting up SSO"""
    success: bool
    provider_id: str
    message: str
