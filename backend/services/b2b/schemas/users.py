"""
User Management Schemas
"""
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    name: Optional[str] = None
    email: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    """User statistics response"""
    total_users: int
    active_users: int
    pending_invitations: int
    managers_count: int


class UserRoleUpdate(BaseModel):
    """Request to update user role"""
    role: str
