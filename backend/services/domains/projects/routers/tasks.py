"""
Task Management API Router

CRUD endpoints for tasks with project/team-based scoping
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.database import get_db
from services.b2b.rbac import require_permission
from services.domains.projects.scope_checker import (
    can_access_project,
    can_access_task,
    validate_team_member_assignment
)
from services.domains.projects.models.task import Task
from services.domains.projects.models.project import Project
from services.domains.projects.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(prefix="/api/domain/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task in a project"""
    # Verify user can access the project
    if not await can_access_project(
        current_user['id'], 
        task_data.project_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project"
        )
    
    # Get project to get team_id
    project = await db.get(Project, task_data.project_id)
    
    # If assigning to someone, validate they're in the team
    if task_data.assigned_to:
        if not await validate_team_member_assignment(
            task_data.assigned_to, 
            project.team_id, 
            db
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of the project's team"
            )
    
    # Create task
    task = Task(
        tenant_id=current_user['tenant_id'],
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        assigned_to=task_data.assigned_to,
        due_date=task_data.due_date,
        created_by=current_user['id']
    )
    
    db.add(task)
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    task = result.scalar_one()
    
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, pattern="^(todo|in_progress|done)$"),
    current_user: dict = require_permission('tasks', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List tasks with optional filtering"""
    query = select(Task).where(Task.deleted_at == None)
    
    # Filter by project if specified
    if project_id:
        if not await can_access_project(
            current_user['id'], 
            project_id, 
            current_user['role'], 
            current_user['tenant_id'],
            db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        query = query.where(Task.project_id == project_id)
    
    # Filter by status if specified
    if status:
        query = query.where(Task.status == status)
    
    result = await db.execute(query.order_by(Task.created_at.desc()))
    tasks = result.scalars().all()
    
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: dict = require_permission('tasks', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Get task details"""
    if not await can_access_task(
        current_user['id'], 
        task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not found or access denied"
        )
    
    task = await db.get(Task, task_id)
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update task details"""
    if not await can_access_task(
        current_user['id'], 
        task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not found or access denied"
        )
    
    task = await db.get(Task, task_id)
    
    # If changing assignee, validate they're in the team
    if task_data.assigned_to:
        project = await db.get(Project, task.project_id)
        if not await validate_team_member_assignment(
            task_data.assigned_to, 
            project.team_id, 
            db
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of the project's team"
            )
    
    # Update fields
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.status is not None:
        task.status = task_data.status
    if task_data.assigned_to is not None:
        task.assigned_to = task_data.assigned_to
    if task_data.due_date is not None:
        task.due_date = task_data.due_date
    
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    task = result.scalar_one()
    
    return task


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    status: str = Query(..., pattern="^(todo|in_progress|done)$"),
    current_user: dict = require_permission('tasks', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update task status only (quick status change)"""
    if not await can_access_task(
        current_user['id'], 
        task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not found or access denied"
        )
    
    task = await db.get(Task, task_id)
    task.status = status
    
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    task = result.scalar_one()
    
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: dict = require_permission('tasks', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """Delete a task"""
    if not await can_access_task(
        current_user['id'], 
        task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task = await db.get(Task, task_id)
    await db.delete(task)
    await db.delete(task)
    
    return None
