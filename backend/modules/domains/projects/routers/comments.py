"""
Comments API Router

Threaded comments on tasks
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.projects.schemas.comments import CommentCreate, CommentUpdate, CommentResponse, CommentResponseWithReplies
from modules.domains.projects.services.comments import (
    create_comment as service_create_comment,
    list_comments_for_task as service_list_comments_for_task,
    update_comment as service_update_comment,
    delete_comment as service_delete_comment
)

router = APIRouter(prefix="/api/domain/comments", tags=["comments"])


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    current_user: dict = require_permission('comments', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new comment"""
    return await service_create_comment(db, current_user, comment_data)


@router.get("/task/{task_id}", response_model=List[CommentResponseWithReplies])
async def list_comments_for_task(
    task_id: UUID,
    current_user: dict = require_permission('comments', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List all comments for a task (threaded)"""
    # Note: list service returns Dicts for thread structure, schema validation will handle serialization
    return await service_list_comments_for_task(db, current_user, task_id)


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    comment_data: CommentUpdate,
    current_user: dict = require_permission('comments', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update a comment (only own comments)"""
    return await service_update_comment(db, current_user, comment_id, comment_data)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: dict = require_permission('comments', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment (only own comments)"""
    await service_delete_comment(db, current_user, comment_id)
    return None

