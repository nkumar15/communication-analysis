from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class Tenant(BaseModel):
    """Tenant model"""
    id: UUID
    name: str
    domain: str  # Email domain for tenant resolution
    firebase_tenant_id: str  # Firebase Identity Platform tenant ID
    activation_token: Optional[str] = None  # Single-use activation token (48-hour expiry)
    activation_status: str = 'pending'  # Status: pending, active, expired
    activation_expires_at: Optional[datetime] = None  # Token expiry timestamp
    activated_at: Optional[datetime] = None  # When tenant was activated
    activated_by: Optional[UUID] = None  # User ID who completed activation
    activation_started_at: Optional[datetime] = None  # Prevent replay attacks
    is_active: bool = True
    domain_type: str = 'default'  # Domain type for multi-domain SaaS (bank_surveillance, etc.)
    features: dict = {}  # Active features and plugins
    created_at: datetime
    updated_at: datetime

class TenantResolutionRequest(BaseModel):
    """Request to resolve tenant from email"""
    email: EmailStr

class TenantResolutionResponse(BaseModel):
    """Response with tenant information"""
    tenant_id: UUID
    tenant_name: str
    domain: str
    firebase_tenant_id: str
    oidc_provider_id: Optional[str] = None  # Primary auth provider ID from auth_providers table
    mobile_oidc_provider_id: Optional[str] = None # Separate provider ID for mobile (if different)
    provider_type: Optional[str] = 'oidc' # 'oidc', 'saml', 'google', etc.

