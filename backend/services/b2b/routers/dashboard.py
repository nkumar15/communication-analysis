"""
Dashboard Router - Role-aware dashboard statistics
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from services.b2b.models import UserModel, Team, TeamMember
from services.b2b.models.team_role_definition import TeamRoleDefinition


router = APIRouter(prefix="/api/b2b/dashboard", tags=["dashboard"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TeamSummary(BaseModel):
    id: str
    name: str
    team_role: str
    team_role_display: Optional[str] = None
    member_count: int
    
    class Config:
        from_attributes = True


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
    
    # Domain stats (team-scoped for member/viewer)
    my_projects_count: int = 0
    my_tasks_count: int = 0
    overdue_tasks_count: int = 0
    
    # Quick actions based on role
    quick_actions: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get role-aware dashboard statistics.
    
    - owner/admin: Full org visibility
    - member/viewer: Team-scoped data
    """
    user_id = current_user['id']
    tenant_id = current_user['tenant_id']
    role = current_user.get('role', 'viewer')
    
    # Determine scope
    is_admin_scope = role in ['owner', 'admin']
    scope = 'org' if is_admin_scope else 'team'
    
    # Get org-wide stats (visible to all per confirmed decision)
    total_users_result = await db.execute(
        select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_id)
    )
    total_users = total_users_result.scalar() or 0
    
    active_users_result = await db.execute(
        select(func.count(UserModel.id)).where(
            UserModel.tenant_id == tenant_id,
            UserModel.is_active == True
        )
    )
    active_users = active_users_result.scalar() or 0
    
    total_teams_result = await db.execute(
        select(func.count(Team.id)).where(Team.tenant_id == tenant_id)
    )
    total_teams = total_teams_result.scalar() or 0
    
    # Pending invitations (admin/owner see all, others see 0)
    pending_invitations = 0
    if is_admin_scope:
        from services.b2b.models import InvitationModel
        pending_result = await db.execute(
            select(func.count(InvitationModel.id)).where(
                InvitationModel.tenant_id == tenant_id,
                InvitationModel.accepted_at.is_(None)
            )
        )
        pending_invitations = pending_result.scalar() or 0
    
    # Get user's teams with role info
    teams_result = await db.execute(
        select(Team, TeamMember, TeamRoleDefinition)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .outerjoin(TeamRoleDefinition, TeamMember.team_role_id == TeamRoleDefinition.id)
        .where(
            Team.tenant_id == tenant_id,
            TeamMember.user_id == user_id
        )
    )
    
    my_teams = []
    team_ids = []
    for team, member, role_def in teams_result:
        team_ids.append(team.id)
        
        # Get member count for each team
        member_count_result = await db.execute(
            select(func.count(TeamMember.id)).where(TeamMember.team_id == team.id)
        )
        member_count = member_count_result.scalar() or 0
        
        my_teams.append(TeamSummary(
            id=str(team.id),
            name=team.name,
            team_role=member.team_role or (role_def.name if role_def else 'team_contributor'),
            team_role_display=role_def.display_name if role_def else None,
            member_count=member_count
        ))
    
    # Domain stats (projects/tasks) - scoped based on role
    my_projects_count = 0
    my_tasks_count = 0
    overdue_tasks_count = 0
    
    try:
        from services.domains.projects.models import Project, Task
        from datetime import datetime, timezone
        
        if is_admin_scope:
            # Admin/owner see all org projects
            projects_result = await db.execute(
                select(func.count(Project.id)).where(Project.tenant_id == tenant_id)
            )
            tasks_result = await db.execute(
                select(func.count(Task.id)).where(Task.tenant_id == tenant_id)
            )
            overdue_result = await db.execute(
                select(func.count(Task.id)).where(
                    Task.tenant_id == tenant_id,
                    Task.due_date < datetime.now(timezone.utc),
                    Task.status != 'done'
                )
            )
        else:
            # Member/viewer see only their teams' projects
            if team_ids:
                projects_result = await db.execute(
                    select(func.count(Project.id)).where(
                        Project.tenant_id == tenant_id,
                        Project.team_id.in_(team_ids)
                    )
                )
                # Tasks need to go through Project to filter by team
                tasks_result = await db.execute(
                    select(func.count(Task.id))
                    .join(Project, Task.project_id == Project.id)
                    .where(
                        Task.tenant_id == tenant_id,
                        Project.team_id.in_(team_ids)
                    )
                )
                overdue_result = await db.execute(
                    select(func.count(Task.id))
                    .join(Project, Task.project_id == Project.id)
                    .where(
                        Task.tenant_id == tenant_id,
                        Project.team_id.in_(team_ids),
                        Task.due_date < datetime.now(timezone.utc),
                        Task.status != 'done'
                    )
                )
            else:
                projects_result = tasks_result = overdue_result = None
        
        if projects_result:
            my_projects_count = projects_result.scalar() or 0
        if tasks_result:
            my_tasks_count = tasks_result.scalar() or 0
        if overdue_result:
            overdue_tasks_count = overdue_result.scalar() or 0
            
    except ImportError:
        # Domain service not available
        pass
    
    # Quick actions based on role
    quick_actions = []
    if role == 'owner':
        quick_actions = ['invite_user', 'create_team', 'manage_billing', 'view_audit_logs']
    elif role == 'admin':
        quick_actions = ['invite_user', 'create_team', 'view_audit_logs']
    elif role == 'member':
        quick_actions = ['view_projects', 'create_task', 'view_teams']
    else:  # viewer
        quick_actions = ['view_projects', 'view_teams']
    
    return DashboardStats(
        role=role,
        scope=scope,
        total_users=total_users,
        active_users=active_users,
        total_teams=total_teams,
        pending_invitations=pending_invitations,
        my_teams=my_teams,
        my_projects_count=my_projects_count,
        my_tasks_count=my_tasks_count,
        overdue_tasks_count=overdue_tasks_count,
        quick_actions=quick_actions
    )
