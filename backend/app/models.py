from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class Tenant(BaseModel):
    """Tenant model"""
    id: UUID
    name: str
    domain: str  # Email domain for tenant resolution
    firebase_tenant_id: str  # Firebase Identity Platform tenant ID
    oidc_provider_id: Optional[str] = None  # OIDC provider ID from Google Cloud (e.g., 'oidc.auth0-xyz')
    activation_token: Optional[str] = None  # Single-use activation token (48-hour expiry)
    activation_status: str = 'pending'  # Status: pending, active, expired
    activation_expires_at: Optional[datetime] = None  # Token expiry timestamp
    activated_at: Optional[datetime] = None  # When tenant was activated
    activated_by: Optional[UUID] = None  # User ID who completed activation
    activation_started_at: Optional[datetime] = None  # Prevent replay attacks
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    """User model - authenticated users only"""
    id: UUID
    tenant_id: UUID
    email: EmailStr
    name: Optional[str] = None
    firebase_uid: str  # Firebase user ID (real UID, not "pending")
    role_id: Optional[UUID] = None  # Foreign key to roles table
    role: Optional[str] = None  # Role slug (e.g., 'admin')
    role_display_name: Optional[str] = None  # Display name of the role (e.g., "Admin", "Field Manager")
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class Invitation(BaseModel):
    """Invitation model - pending invitations"""
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str = 'member'
    invitation_token: str
    invited_by: Optional[UUID] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[UUID] = None  # Audit: who accepted
    accepted_from_ip: Optional[str] = None  # Audit: IP address
    created_at: datetime
    updated_at: datetime


# Request/Response models

class TenantResolutionRequest(BaseModel):
    """Request to resolve tenant from email"""
    email: EmailStr


class TenantResolutionResponse(BaseModel):
    """Response with tenant information"""
    tenant_id: UUID
    tenant_name: str
    domain: str
    firebase_tenant_id: str
    oidc_provider_id: Optional[str] = None


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    email: str
    name: Optional[str] = None
    role: Optional[str] = None  # Role slug (e.g., "admin", "field_manager")
    role_display_name: Optional[str] = None  # Role display name (e.g., "Admin", "Field Manager")
    tenant_id: UUID
    tenant_name: str


class InvitationRequest(BaseModel):
    """Request to create invitation"""
    email: EmailStr
    role: str = 'member'


class InvitationResponse(BaseModel):
    """Invitation information response"""
    id: UUID
    email: str
    role: str
    expires_at: datetime
    invitation_url: str
