from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.db.session import get_db
from services.b2c.middleware.b2c_auth import get_current_b2c_user
from services.b2c.services.todos.service import todo_service

router = APIRouter()

# --- Schemas ---
class TodoCreate(BaseModel):
    title: str 
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    due_date: Optional[datetime] = None

class TodoResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: Optional[str]
    is_completed: bool
    due_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/{workspace_id}/todos", response_model=TodoResponse)
async def create_todo(
    workspace_id: str,
    todo: TodoCreate,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new todo in the workspace"""
    return await todo_service.create_todo(
        db, 
        UUID(workspace_id), 
        UUID(str(current_user['id'])), 
        todo.model_dump()
    )

@router.get("/{workspace_id}/todos", response_model=List[TodoResponse])
async def list_todos(
    workspace_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """List all todos in the workspace"""
    return await todo_service.list_todos(
        db, 
        UUID(workspace_id), 
        UUID(str(current_user['id']))
    )

@router.patch("/{workspace_id}/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(
    workspace_id: str,
    todo_id: str,
    todo: TodoUpdate,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a todo"""
    return await todo_service.update_todo(
        db, 
        UUID(workspace_id), 
        UUID(todo_id), 
        UUID(str(current_user['id'])), 
        todo.model_dump(exclude_unset=True)
    )

@router.delete("/{workspace_id}/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    workspace_id: str,
    todo_id: str,
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a todo"""
    await todo_service.delete_todo(
        db, 
        UUID(workspace_id), 
        UUID(todo_id), 
        UUID(str(current_user['id']))
    )
