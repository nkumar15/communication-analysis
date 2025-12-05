"""Task schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., max_length=200, description="Task title")
    description: Optional[str] = Field(None, description="Task description")


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    project_id: UUID = Field(..., description="Project ID this task belongs to")
    assigned_to: Optional[UUID] = Field(None, description="User ID to assign task to")
    due_date: Optional[date] = Field(None, description="Task due date")


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    assigned_to: Optional[UUID] = None
    due_date: Optional[date] = None


class TaskResponse(TaskBase):
    """Schema for task response"""
    id: UUID
    tenant_id: UUID
    project_id: UUID
    status: str
    assigned_to: Optional[UUID]
    due_date: Optional[date]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
