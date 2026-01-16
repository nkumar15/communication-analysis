from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List

# ============================================================================
# Team Schemas
# ============================================================================

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Team name")
    description: Optional[str] = Field(None, max_length=1000, description="Team description")
    config_data: Dict[str, Any] = Field(default_factory=dict, description="Additional team configuration")
    parent_team_id: Optional[UUID] = Field(None, description="Parent team ID for hierarchy")
    team_type: str = Field("standard", description="Team type (standard/hierarchical)")

class TeamCreate(TeamBase):
    """Schema for creating a new team"""
    pass

class TeamUpdate(BaseModel):
    """Schema for updating team details"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config_data: Optional[Dict[str, Any]] = None

class TeamResponse(TeamBase):
    """Schema for team response with full details"""
    id: UUID
    tenant_id: UUID
    is_default: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    member_count: int = 0
    org_tier: Optional[str] = None
    
    class Config:
        from_attributes = True

class TeamListResponse(BaseModel):
    """Schema for team list item"""
    id: UUID
    name: str
    description: Optional[str]
    is_default: bool
    member_count: int = 0
    created_at: datetime
    parent_team_id: Optional[UUID] = None
    org_tier: Optional[str] = None
    
    class Config:
        from_attributes = True

# ============================================================================
# Team Member Schemas
# ============================================================================

class TeamMemberAdd(BaseModel):
    """Schema for adding a user to a team"""
    user_id: UUID
    team_role: str = Field(
        ...,  # Required - no default, frontend must select a role
        min_length=1,
        max_length=50,
        description="Role within the team (from team_role_definitions)"
    )

class TeamMemberUpdate(BaseModel):
    """Schema for updating team member role"""
    team_role: str = Field(
        ..., 
        min_length=1,
        max_length=50,
        description="New role for the team member (from team_role_definitions)"
    )

class TeamMemberResponse(BaseModel):
    """Schema for team member with user details"""
    id: UUID
    team_id: UUID
    user_id: UUID
    team_role: str
    user_email: Optional[EmailStr] = None
    user_name: Optional[str] = None
    joined_at: datetime
    
    class Config:
        from_attributes = True

class MoveUserRequest(BaseModel):
    """Schema for moving user between teams"""
    from_team_id: UUID
    to_team_id: UUID
    team_role: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Role in the destination team"
    )

# ============================================================================
# Team Statistics
# ============================================================================

class TeamStatsResponse(BaseModel):
    """Schema for team statistics"""
    total_teams: int
    default_team_id: Optional[UUID]
    user_teams_count: int  # Number of teams current user belongs to
    
    class Config:
        from_attributes = True
