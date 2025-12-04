from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class Invitation(BaseModel):
    """Invitation model - pending invitations"""
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: str = 'member'
    invitation_token: str
    invited_by: Optional[UUID] = None
    team_id: Optional[UUID] = None
    team_role: Optional[str] = None  # NEW: Team role to assign on acceptance
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[UUID] = None  # Audit: who accepted
    accepted_from_ip: Optional[str] = None  # Audit: IP address
    created_at: datetime
    updated_at: datetime

class InvitationRequest(BaseModel):
    """Request to create invitation"""
    email: EmailStr
    role: str = 'member'
    team_id: Optional[UUID] = None      # NEW: Optional team assignment
    team_role: Optional[str] = None     # NEW: Team role (required if team_id provided)

class InvitationResponse(BaseModel):
    """Invitation information response"""
    id: UUID
    expires_at: datetime
    invitation_url: str
