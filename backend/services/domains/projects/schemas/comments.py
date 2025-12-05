"""Comment schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class CommentBase(BaseModel):
    """Base comment schema"""
    content: str = Field(..., min_length=1, description="Comment content")


class CommentCreate(CommentBase):
    """Schema for creating a comment"""
    task_id: UUID = Field(..., description="Task ID this comment belongs to")
    parent_comment_id: Optional[UUID] = Field(None, description="Parent comment ID for threaded replies")


class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: Optional[str] = Field(None, min_length=1)


class CommentResponse(CommentBase):
    """Schema for comment response (no nested replies)"""
    id: UUID
    tenant_id: UUID
    task_id: UUID
    parent_comment_id: Optional[UUID]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommentResponseWithReplies(CommentResponse):
    """Schema for comment response with nested replies"""
    replies: List['CommentResponseWithReplies'] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# Update forward reference
CommentResponseWithReplies.model_rebuild()
