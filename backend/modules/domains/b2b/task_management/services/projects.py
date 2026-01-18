from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from modules.domains.b2b.task_management.models.project import Project
from modules.domains.b2b.task_management.schemas.projects import ProjectCreate, ProjectUpdate
from modules.domains.b2b.task_management.scope_checker import (
    get_accessible_projects_query,
    can_access_project,
    can_user_access_team,
    can_perform_action,
)
from modules.b2b.rbac.permission_checker import has_permission

async def create_project(db: AsyncSession, user: dict, project_data: ProjectCreate) -> Project:
    """Create a new project with permission checks"""
    # 1. Verify user can access this team
    if not await can_user_access_team(
        user['id'], 
        project_data.team_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this team"
        )

    # 2. Check Permission: Either global write OR team write capability
    # Global Admin/Owner check
    has_global_write = await has_permission(user['id'], 'projects', 'write', db)
    
    # Team Manager/Member capability check
    can_team_write = await can_perform_action(
        user['id'],
        project_data.team_id,
        'projects',
        'write',
        user['role'],
        db
    )
    
    if not (has_global_write or can_team_write):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create projects in this team"
        )
    
    # Create project
    project = Project(
        tenant_id=user['tenant_id'],
        team_id=project_data.team_id,
        name=project_data.name,
        description=project_data.description,
        created_by=user['id']
    )
    
    db.add(project)
    await db.flush()
    result = await db.execute(select(Project).where(Project.id == project.id))
    return result.scalar_one()


async def list_projects(db: AsyncSession, user: dict) -> List[Project]:
    """List accessible projects"""
    query = await get_accessible_projects_query(
        user['id'], 
        user['role'], 
        user['tenant_id'],
        db
    )
    
    result = await db.execute(query.order_by(Project.created_at.desc()))
    return result.scalars().all()


async def get_project(db: AsyncSession, user: dict, project_id: UUID) -> Project:
    """Get specific project"""
    if not await can_access_project(
        user['id'], 
        project_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project not found or access denied"
        )
    
    project = await db.get(Project, project_id)
    return project


async def update_project(db: AsyncSession, user: dict, project_id: UUID, project_data: ProjectUpdate) -> Project:
    """Update project"""
    if not await can_access_project(
        user['id'], 
        project_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project not found or access denied"
        )
    
    project = await db.get(Project, project_id)
    
    # Check team role capability
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'projects',
        'write',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow editing projects"
        )
    
    # Update fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        project.status = project_data.status
    
    await db.flush()
    result = await db.execute(select(Project).where(Project.id == project.id))
    return result.scalar_one()


async def delete_project(db: AsyncSession, user: dict, project_id: UUID) -> None:
    """Delete project"""
    if not await can_access_project(
        user['id'], 
        project_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project = await db.get(Project, project_id)
    
    # Check team role capability
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'projects',
        'delete',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow deleting projects"
        )
    
    await db.delete(project)
