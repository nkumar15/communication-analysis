from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID
from core.constants import B2BRoleName


class Invitation(BaseModel):
    """Invitation model - pending invitations"""
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str = 'member'
    invitation_token: str
    invited_by: Optional[UUID] = None
    team_id: Optional[UUID] = None
    team_role: Optional[str] = None
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[UUID] = None
    accepted_from_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InvitationRequest(BaseModel):
    """Request to create invitation"""
    email: EmailStr
    role: str = 'member'
    team_id: Optional[UUID] = None
    team_role: Optional[str] = None


class InvitationResponse(BaseModel):
    """Invitation information response"""
    id: UUID
    expires_at: datetime
    invitation_url: str


# Router-specific schemas
class InviteUserRequest(BaseModel):
    """Request to invite a new user"""
    email: str
    role: str = B2BRoleName.VIEWER
    team_id: Optional[UUID] = None
    team_role: Optional[str] = None


class InviteUserResponse(BaseModel):
    """Response after inviting a user"""
    invitation_id: UUID
    email: str
    status: str
    message: str
    team_id: Optional[UUID] = None


class InvitationListResponse(BaseModel):
    """Response for listing invitations"""
    id: UUID
    email: str
    role: str
    invited_by: Optional[UUID]
    team_id: Optional[UUID]
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
