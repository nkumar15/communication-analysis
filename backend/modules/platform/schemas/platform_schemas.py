"""
Platform API Schemas

Pydantic models for platform admin API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


# --- Tenant Onboarding ---

class TenantOnboardRequest(BaseModel):
    """Request schema for tenant onboarding"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Company/tenant name")
    domain: str = Field(..., min_length=3, max_length=255, description="Email domain (e.g., acme.com)")
    owner_email: EmailStr = Field(..., description="Owner/admin email address")


class TenantOnboardResponse(BaseModel):
    """Response schema for successful tenant onboarding"""
    tenant_id: str
    tenant_name: str
    domain: str
    owner_email: str
    firebase_tenant_id: str
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


# --- B2B Plans ---

class B2BPlanCreate(BaseModel):
    """Schema for creating a new B2B plan version"""
    tier_key: str = Field(..., description="Logical tier key (e.g. starter, professional)")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    
    # Pricing
    base_price_monthly: int = Field(0, ge=0, description="Base price in cents/month")
    base_price_yearly: int = Field(0, ge=0, description="Base price in cents/year")
    per_seat_price_monthly: int = Field(0, ge=0, description="Per-seat price in cents/month")
    per_seat_price_yearly: int = Field(0, ge=0, description="Per-seat price in cents/year")
    
    # Configuration
    limits: dict = Field(default_factory=dict, description="Resource limits (e.g. projects, storage)")
    features: dict = Field(default_factory=dict, description="Feature flags")
    provider_config: dict = Field(default_factory=dict, description="Provider mapping (e.g. Stripe IDs)")
    
    effective_from: Optional[datetime] = None


class B2BPlanResponse(BaseModel):
    """Response schema for B2B plan details"""
    id: UUID
    tier_key: str
    name: str
    description: Optional[str]
    
    base_price_monthly: int
    base_price_yearly: int
    per_seat_price_monthly: int
    per_seat_price_yearly: int
    
    limits: dict
    features: dict
    provider_config: dict
    
    effective_from: datetime
    archived_at: Optional[datetime]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
