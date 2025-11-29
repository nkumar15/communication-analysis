from pydantic import BaseModel, EmailStr
from typing import Optional
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

class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    email: str
    name: Optional[str] = None
    role: Optional[str] = None  # Role slug (e.g., "admin", "field_manager")
    role_display_name: Optional[str] = None  # Role display name (e.g., "Admin", "Field Manager")
    tenant_id: UUID
    tenant_name: str
