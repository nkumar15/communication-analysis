"""
User Management Schemas
"""
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


class TeamMembership(BaseModel):
    """Team membership info for a user"""
    team_id: UUID
    team_name: str
    team_role: Optional[str] = None


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    name: Optional[str] = None
    email: EmailStr
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    teams: List[TeamMembership] = []
    
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
