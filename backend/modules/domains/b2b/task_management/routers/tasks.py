"""
Task Management API Router

CRUD endpoints for tasks with project/team-based scoping
"""
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.task_management.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse
from modules.domains.b2b.task_management.services.tasks import (
    create_task as service_create_task,
    list_tasks as service_list_tasks,
    get_task as service_get_task,
    update_task as service_update_task,
    update_task_status as service_update_task_status,
    delete_task as service_delete_task
)

router = APIRouter(prefix="/api/b2b/domain/task_management/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task in a project"""
    return await service_create_task(db, current_user, task_data)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, pattern="^(todo|in_progress|done)$"),
    current_user: dict = require_permission('tasks', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List tasks with optional filtering"""
    return await service_list_tasks(db, current_user, project_id, status)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: dict = require_permission('tasks', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Get task details"""
    return await service_get_task(db, current_user, task_id)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update task details"""
    return await service_update_task(db, current_user, task_id, task_data)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    status: str = Query(..., pattern="^(todo|in_progress|done)$"),
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update task status only (quick status change)"""
    return await service_update_task_status(db, current_user, task_id, status)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: dict = require_permission('tasks', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task"""
    await service_delete_task(db, current_user, task_id)
    return None

