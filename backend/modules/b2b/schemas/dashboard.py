"""
Dashboard Schemas

Schemas for dashboard statistics and summaries.
"""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class TeamSummary(BaseModel):
    """Summary of a team for dashboard display"""
    id: str
    name: str
    team_role: str
    team_role_display: Optional[str] = None
    member_count: int
    
    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    """Role-aware dashboard statistics"""
    role: str
    scope: str  # 'org' for admin/owner, 'team' for member/viewer
    
    # Org-wide stats (visible to all per spec)
    total_users: int
    active_users: int
    total_teams: int
    pending_invitations: int
    
    # User's teams
    my_teams: List[TeamSummary]

    # Quick actions based on role
    quick_actions: List[str]
