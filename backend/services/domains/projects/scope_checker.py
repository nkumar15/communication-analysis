"""
Scope checker for team-based access control

Implements hierarchical access patterns:
- Owner/Admin: Can access all projects in tenant
- Team members: Can only access projects from their teams
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from services.b2b.models.user import UserModel
from services.b2b.models.team_member import TeamMember
from services.domains.projects.models.project import Project
from services.domains.projects.models.task import Task


from services.b2b.models.team import Team

async def get_user_team_ids(user_id: UUID, db: AsyncSession) -> List[UUID]:
    """Get all team IDs that the user is a member of"""
    query = select(TeamMember.team_id).where(TeamMember.user_id == user_id)
    result = await db.execute(query)
    return [row[0] for row in result.all()]


async def can_user_access_team(user_id: UUID, team_id: UUID, user_role: str, user_tenant_id: UUID, db: AsyncSession) -> bool:
    """Check if user can access a specific team"""
    # First verify team belongs to user's tenant
    team = await db.get(Team, team_id)
    if not team or team.tenant_id != user_tenant_id:
        return False

    # Owner/Admin can access all teams in their tenant
    if user_role in ['owner', 'admin']:
        return True
    
    # Check if user is member of the team
    user_teams = await get_user_team_ids(user_id, db)
    return team_id in user_teams


async def get_accessible_projects_query(user_id: UUID, user_role: str, user_tenant_id: UUID, db: AsyncSession):
    """Get query for projects accessible to user (team-scoped)"""
    # Owner/Admin can see all projects in tenant
    if user_role in ['owner', 'admin']:
        return select(Project).where(
            Project.tenant_id == user_tenant_id,
            Project.deleted_at == None
        )
    
    # Regular users see only projects from their teams (which are implicitly in tenant)
    user_teams = await get_user_team_ids(user_id, db)
    return select(Project).where(
        Project.team_id.in_(user_teams),
        Project.tenant_id == user_tenant_id,
        Project.deleted_at == None
    )


async def can_access_project(user_id: UUID, project_id: UUID, user_role: str, user_tenant_id: UUID, db: AsyncSession) -> bool:
    """Check if user can access a specific project"""
    project = await db.get(Project, project_id)
    if not project or project.deleted_at:
        return False
    
    # Verify tenant isolation
    if project.tenant_id != user_tenant_id:
        return False
    
    return await can_user_access_team(user_id, project.team_id, user_role, user_tenant_id, db)


async def can_access_task(user_id: UUID, task_id: UUID, user_role: str, user_tenant_id: UUID, db: AsyncSession) -> bool:
    """Check if user can access a specific task (via project's team)"""
    task = await db.get(Task, task_id)
    if not task or task.deleted_at:
        return False
    
    # Get the project separately to avoid greenlet issues
    project = await db.get(Project, task.project_id)
    if not project:
        return False
    
    # Verify tenant isolation via project
    if project.tenant_id != user_tenant_id:
        return False
    
    return await can_user_access_team(user_id, project.team_id, user_role, user_tenant_id, db)



async def validate_team_member_assignment(assignee_id: UUID, team_id: UUID, db: AsyncSession) -> bool:
    """Validate that assignee is a member of the team"""
    user_teams = await get_user_team_ids(assignee_id, db)
    return team_id in user_teams

