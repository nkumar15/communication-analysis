"""
Project Management API Router

CRUD endpoints for projects with team-based scoping:
- Team members: Can manage projects in their teams
- Owner/Admin: Can manage all projects in tenant
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from core.database import get_db
from services.b2b.rbac import require_permission
from services.domains.projects.scope_checker import (
    get_accessible_projects_query,
    can_access_project,
    can_user_access_team,
    can_perform_action,
    can_write_in_team,
    can_delete_in_team
)
from services.domains.projects.models.project import Project
from services.domains.projects.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api/domain/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = require_permission('projects', 'read'),  # Relaxed to read for entry
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project
    
    Permission required: projects:write OR (projects:read AND team_manager of target team)
    User must be a member of the specified team or be owner/admin.
    """
    from services.b2b.rbac.permission_checker import has_permission
    
    # 1. Verify user can access this team
    if not await can_user_access_team(
        current_user['id'], 
        project_data.team_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this team"
        )

    # 2. Check Permission: Either global write OR team write capability
    # Global Admin/Owner check
    has_global_write = await has_permission(current_user['id'], 'projects', 'write', db)
    
    # Team Manager/Member capability check
    can_team_write = await can_perform_action(
        current_user['id'],
        project_data.team_id,
        'projects',
        'write',
        current_user['role'],
        db
    )
    
    if not (has_global_write or can_team_write):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create projects in this team"
        )
    
    # Create project
    project = Project(
        tenant_id=current_user['tenant_id'],
        team_id=project_data.team_id,
        name=project_data.name,
        description=project_data.description,
        created_by=current_user['id']
    )
    
    db.add(project)
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Project).where(Project.id == project.id))
    project = result.scalar_one()
    
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects accessible to current user (team-scoped)
    
    Permission required: projects:read
    
    Scope:
    - Owner/Admin: All projects in tenant
    - Team members: Projects from their teams
    """
    query = await get_accessible_projects_query(
        current_user['id'], 
        current_user['role'], 
        current_user['tenant_id'],
        db
    )
    
    result = await db.execute(query.order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific project's details
    
    Permission required: projects:read
    Returns 404 if project doesn't exist or user doesn't have access.
    """
    if not await can_access_project(
        current_user['id'], 
        project_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project not found or access denied"
        )
    
    project = await db.get(Project, project_id)
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: dict = require_permission('projects', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update project details
    
    Permission required: projects:write
    """
    if not await can_access_project(
        current_user['id'], 
        project_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project not found or access denied"
        )
    
    project = await db.get(Project, project_id)
    
    # Check team role capability: can_write_resources (project specific)
    if not await can_perform_action(
        current_user['id'],
        project.team_id,
        'projects',
        'write',
        current_user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow editing projects"
        )
    
    # Update provided fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.status is not None:
        project.status = project_data.status
    
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Project).where(Project.id == project.id))
    project = result.scalar_one()
    
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: dict = require_permission('projects', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a project
    
    Permission required: projects:delete
    """
    if not await can_access_project(
        current_user['id'], 
        project_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project = await db.get(Project, project_id)
    
    # Check team role capability: can_delete_resources
    if not await can_perform_action(
        current_user['id'],
        project.team_id,
        'projects',
        'delete',
        current_user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow deleting projects"
        )
    
    await db.delete(project)
    
    return None
