from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from modules.domains.b2b.task_management.models.task import Task
from modules.domains.b2b.task_management.models.project import Project
from modules.domains.b2b.task_management.schemas.tasks import TaskCreate, TaskUpdate
from modules.domains.b2b.task_management.scope_checker import (
    can_access_project,
    can_access_task,
    validate_team_member_assignment,
    can_perform_action,
)

async def create_task(db: AsyncSession, user: dict, task_data: TaskCreate) -> Task:
    """Create a new task"""
    # Verify user can access the project
    if not await can_access_project(
        user['id'], 
        task_data.project_id, 
        user['role'], 
        user['tenant_id'],
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
    
    # Check team role capability: tasks:write
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'tasks',
        'write',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow creating tasks"
        )
    
    # Create task
    task = Task(
        tenant_id=user['tenant_id'],
        project_id=task_data.project_id,
        title=task_data.title,
        description=task_data.description,
        assigned_to=task_data.assigned_to,
        due_date=task_data.due_date,
        created_by=user['id']
    )
    
    db.add(task)
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    return result.scalar_one()


async def list_tasks(db: AsyncSession, user: dict, project_id: Optional[UUID] = None, status_filter: Optional[str] = None) -> List[Task]:
    """List tasks with optional filtering"""
    query = select(Task).where(Task.deleted_at == None)
    
    # Filter by project if specified
    if project_id:
        if not await can_access_project(
            user['id'], 
            project_id, 
            user['role'], 
            user['tenant_id'],
            db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        query = query.where(Task.project_id == project_id)
    
    # Filter by status if specified
    if status_filter:
        query = query.where(Task.status == status_filter)
    
    result = await db.execute(query.order_by(Task.created_at.desc()))
    return result.scalars().all()


async def get_task(db: AsyncSession, user: dict, task_id: UUID) -> Task:
    """Get task details"""
    if not await can_access_task(
        user['id'], 
        task_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not found or access denied"
        )
    
    task = await db.get(Task, task_id)
    return task


async def update_task(db: AsyncSession, user: dict, task_id: UUID, task_data: TaskUpdate) -> Task:
    """Update task details"""
    if not await can_access_task(
        user['id'], 
        task_id, 
        user['role'], 
        user['tenant_id'],
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
    else:
        project = await db.get(Project, task.project_id)
    
    # Check team role capability: tasks:write
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'tasks',
        'write',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow editing tasks"
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
    
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    return result.scalar_one()


async def update_task_status(db: AsyncSession, user: dict, task_id: UUID, status_val: str) -> Task:
    """Update task status only"""
    if not await can_access_task(
        user['id'], 
        task_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task not found or access denied"
        )
    
    task = await db.get(Task, task_id)
    task.status = status_val
    
    await db.flush()
    result = await db.execute(select(Task).where(Task.id == task.id))
    return result.scalar_one()


async def delete_task(db: AsyncSession, user: dict, task_id: UUID) -> None:
    """Delete a task"""
    if not await can_access_task(
        user['id'], 
        task_id, 
        user['role'], 
        user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task = await db.get(Task, task_id)
    project = await db.get(Project, task.project_id)
    
    # Check team role capability: can_delete_resources
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'tasks',
        'delete',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow deleting tasks"
        )
    
    await db.delete(task)
