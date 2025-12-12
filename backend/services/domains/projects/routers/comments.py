"""
Comments API Router

Threaded comments on tasks
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from core.database import get_db
from services.b2b.rbac import require_permission
from services.domains.projects.scope_checker import can_access_task, can_write_in_team
from services.domains.projects.models.comment import Comment
from services.domains.projects.models.task import Task
from services.domains.projects.models.project import Project
from services.domains.projects.schemas.comments import CommentCreate, CommentUpdate, CommentResponse, CommentResponseWithReplies

router = APIRouter(prefix="/api/domain/comments", tags=["comments"])


def build_comment_tree(comments: List[Comment]) -> List[dict]:
    """Build threaded comment tree from flat list"""
    # Convert to dicts first to avoid lazy loading issues during Pydantic validation
    comment_map = {}
    for c in comments:
        c_dict = {
            "id": c.id,
            "tenant_id": c.tenant_id,
            "task_id": c.task_id,
            "parent_comment_id": c.parent_comment_id,
            "created_by": c.created_by,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "content": c.content,
            "replies": []
        }
        comment_map[c.id] = c_dict
    
    # Build tree structure
    root_comments = []
    for c in comments:
        c_dict = comment_map[c.id]
        if c.parent_comment_id is None:
            root_comments.append(c_dict)
        else:
            parent = comment_map.get(c.parent_comment_id)
            if parent:
                parent['replies'].append(c_dict)
    
    return root_comments


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    current_user: dict = require_permission('comments', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new comment"""
    # Verify user can access the task
    if not await can_access_task(
        current_user['id'], 
        comment_data.task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )
    
    # If replying to a comment, verify it exists and belongs to same task
    if comment_data.parent_comment_id:
        parent = await db.get(Comment, comment_data.parent_comment_id)
        if not parent or parent.task_id != comment_data.task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent comment"
            )
    
    # Get task and project for capability check
    task = await db.get(Task, comment_data.task_id)
    project = await db.get(Project, task.project_id)
    
    # Check team role capability: can_write_resources
    if not await can_write_in_team(
        current_user['id'],
        project.team_id,
        current_user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow creating comments"
        )
    
    # Create comment
    comment = Comment(
        tenant_id=current_user['tenant_id'],
        task_id=comment_data.task_id,
        content=comment_data.content,
        parent_comment_id=comment_data.parent_comment_id,
        created_by=current_user['id']
    )
    
    db.add(comment)
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Comment).where(Comment.id == comment.id))
    comment = result.scalar_one()
    
    return comment


@router.get("/task/{task_id}", response_model=List[CommentResponseWithReplies])
async def list_comments_for_task(
    task_id: UUID,
    current_user: dict = require_permission('comments', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List all comments for a task (threaded)"""
    # Verify user can access the task
    if not await can_access_task(
        current_user['id'], 
        task_id, 
        current_user['role'], 
        current_user['tenant_id'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )
    
    # Get all comments for the task
    query = select(Comment).where(
        Comment.task_id == task_id,
        Comment.deleted_at == None
    ).order_by(Comment.created_at.asc())
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    # Build threaded structure
    threaded_comments = build_comment_tree(comments)
    
    return threaded_comments


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    comment_data: CommentUpdate,
    current_user: dict = require_permission('comments', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Update a comment (only own comments)"""
    comment = await db.get(Comment, comment_id)
    
    if not comment or comment.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Verify tenant isolation
    if comment.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only owner or comment author can edit
    if current_user['role'] not in ['owner', 'admin'] and comment.created_by != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments"
        )
    
    # Update content
    if comment_data.content is not None:
        comment.content = comment_data.content
    
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(Comment).where(Comment.id == comment.id))
    comment = result.scalar_one()
    
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: dict = require_permission('comments', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment (only own comments)"""
    comment = await db.get(Comment, comment_id)
    
    if not comment or comment.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Verify tenant isolation
    if comment.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only owner or comment author can delete
    if current_user['role'] not in ['owner', 'admin'] and comment.created_by != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    await db.delete(comment)
    
    return None

