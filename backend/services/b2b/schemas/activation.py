"""
Activation Schemas

Schemas for tenant activation workflow.
"""
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ActivationValidationResponse(BaseModel):
    """Response for activation token validation"""
    tenant_id: UUID
    tenant_name: str
    domain: str
    admin_email: str
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
