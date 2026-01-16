from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

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


class TeamMembership(BaseModel):
    """User's membership in a team"""
    id: UUID
    name: str
    team_role: str  # team_manager, team_contributor, team_reader


class UserResponse(BaseModel):
    """User information response with permissions for frontend"""
    id: UUID
    email: str
    name: Optional[str] = None
    role: Optional[str] = None  # Role slug (e.g., "admin", "member")
    role_display_name: Optional[str] = None  # Role display name (e.g., "Admin", "Member")
    tenant_id: UUID
    tenant_name: str
    domain_type: str = "default"  # Domain type for sidebar (bank_surveillance, marketing_agency, etc.)
    # Frontend permission checking
    # Frontend permission checking
    permissions: List[str] = []  # ["projects:read", "users:invite", ...]
    teams: List[TeamMembership] = []  # Teams user belongs to
    active_plugins: List[str] = []  # Legacy: List of plugin names
    active_features: dict = {}  # New: Full feature configuration incl. plugins

