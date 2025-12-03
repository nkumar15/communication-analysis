"""
Platform API Schemas

Pydantic models for platform admin API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# --- Tenant Onboarding ---

class TenantOnboardRequest(BaseModel):
    """Request schema for tenant onboarding"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Company/tenant name")
    domain: str = Field(..., min_length=3, max_length=255, description="Email domain (e.g., acme.com)")
    owner_email: EmailStr = Field(..., description="Owner/admin email address")
    oidc_provider: str = Field(..., description="OIDC provider type: auth0, okta, google, azure")
    oidc_client_id: str = Field(..., min_length=1, description="OIDC client ID")
    oidc_client_secret: str = Field(..., min_length=1, description="OIDC client secret")
    oidc_issuer: str = Field(..., min_length=1, description="OIDC issuer URL")


class TenantOnboardResponse(BaseModel):
    """Response schema for successful tenant onboarding"""
    tenant_id: str
    tenant_name: str
    domain: str
    owner_email: str
    firebase_tenant_id: str
    oidc_provider_id: str
    activation_url: str
    activation_token: str
    expires_at: str
    message: str = "Tenant onboarded successfully. Activation email sent."


# --- Tenant Details ---

class AuthProviderInfo(BaseModel):
    """Auth provider information"""
    provider_type: str
    provider_id: str
    display_name: Optional[str]
    is_primary: bool
    is_active: bool


class TenantDetailResponse(BaseModel):
    """Detailed tenant information"""
    id: UUID
    name: str
    domain: str
    firebase_tenant_id: str
    activation_status: str
    activation_token: Optional[str] = None
    activation_expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    # Stats
    user_count: int
    team_count: int
    
    # Auth provider
    auth_provider: Optional[AuthProviderInfo] = None


# --- Resend Activation ---

class ResendActivationResponse(BaseModel):
    """Response for resend activation request"""
    tenant_id: str
    activation_url: str
    expires_at: str
    message: str = "Activation email resent successfully"


# --- Deactivate Tenant ---

class DeactivateTenantResponse(BaseModel):
    """Response for tenant deactivation"""
    tenant_id: str
    message: str = "Tenant deactivated successfully"
