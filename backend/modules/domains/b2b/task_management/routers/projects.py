"""
Project Management API Router

CRUD endpoints for projects with team-based scoping:
- Team members: Can manage projects in their teams
- Owner/Admin: Can manage all projects in tenant
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.task_management.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse
from modules.domains.b2b.task_management.services.projects import (
    create_project as service_create_project,
    list_projects as service_list_projects,
    get_project as service_get_project,
    update_project as service_update_project,
    delete_project as service_delete_project
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new project
    """
    return await service_create_project(db, current_user, project_data)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects accessible to current user (team-scoped)
    """
    return await service_list_projects(db, current_user)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific project's details
    """
    return await service_get_project(db, current_user, project_id)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: dict = require_permission('projects', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update project details
    """
    return await service_update_project(db, current_user, project_id, project_data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: dict = require_permission('projects', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a project
    """
    await service_delete_project(db, current_user, project_id)
    return None
