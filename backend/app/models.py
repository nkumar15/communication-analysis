from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class Tenant(BaseModel):
    """Tenant model"""
    id: int
    name: str
    domain: str  # Email domain for tenant resolution
    firebase_tenant_id: str  # Firebase Identity Platform tenant ID
    oidc_provider_id: Optional[str] = None  # OIDC provider ID from Google Cloud (e.g., 'oidc.auth0-xyz')
    activation_token: Optional[str] = None  # Single-use activation token (48-hour expiry)
    activation_status: str = 'pending'  # Status: pending, active, expired
    activation_expires_at: Optional[datetime] = None  # Token expiry timestamp
    activated_at: Optional[datetime] = None  # When tenant was activated
    activated_by: Optional[int] = None  # User ID who completed activation
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    """User model"""
    id: int
    tenant_id: int
    email: EmailStr
    name: Optional[str] = None
    firebase_uid: str  # Firebase user ID
    role: str = 'member'  # Role: admin, manager, member
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TenantResolutionRequest(BaseModel):
    """Request to resolve tenant from email"""
    email: EmailStr


class TenantResolutionResponse(BaseModel):
    """Response with tenant information"""
    tenant_id: int
    tenant_name: str
    domain: str
    firebase_tenant_id: str  # Frontend needs this to set Firebase auth context
    oidc_provider_id: Optional[str] = None  # OIDC provider ID to use for sign-in


class UserResponse(BaseModel):
    """User information response"""
    id: int
    email: str
    name: Optional[str] = None
    role: str  # admin, manager, member
    tenant_id: int
    tenant_name: str
