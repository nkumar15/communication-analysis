from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict
from uuid import UUID
from fastapi import HTTPException, status

from modules.domains.b2b.task_management.models.comment import Comment
from modules.domains.b2b.task_management.models.task import Task
from modules.domains.b2b.task_management.models.project import Project
from modules.domains.b2b.task_management.schemas.comments import CommentCreate, CommentUpdate
from modules.domains.b2b.task_management.scope_checker import can_access_task, can_perform_action

def build_comment_tree(comments: List[Comment]) -> List[dict]:
    """Build threaded comment tree from flat list"""
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


async def create_comment(db: AsyncSession, user: dict, comment_data: CommentCreate) -> Comment:
    """Create a new comment"""
    # Verify user can access the task
    if not await can_access_task(
        user['id'], 
        comment_data.task_id, 
        user['role'], 
        user['tenant_id'],
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
    if not await can_perform_action(
        user['id'],
        project.team_id,
        'comments',
        'write',
        user['role'],
        db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your team role doesn't allow creating comments"
        )
    
    # Create comment
    comment = Comment(
        tenant_id=user['tenant_id'],
        task_id=comment_data.task_id,
        content=comment_data.content,
        parent_comment_id=comment_data.parent_comment_id,
        created_by=user['id']
    )
    
    db.add(comment)
    await db.flush()
    result = await db.execute(select(Comment).where(Comment.id == comment.id))
    return result.scalar_one()


async def list_comments_for_task(db: AsyncSession, user: dict, task_id: UUID) -> List[dict]:
    """List all comments for a task (threaded)"""
    # Verify user can access the task
    if not await can_access_task(
        user['id'], 
        task_id, 
        user['role'], 
        user['tenant_id'],
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
    
    return build_comment_tree(comments)


async def update_comment(db: AsyncSession, user: dict, comment_id: UUID, comment_data: CommentUpdate) -> Comment:
    """Update a comment"""
    comment = await db.get(Comment, comment_id)
    
    if not comment or comment.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if comment.tenant_id != user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only owner or comment author can edit
    from infrastructure.logging import get_logger
    logger = get_logger(__name__)
    logger.info("DEBUG COMMENTS: update check", 
                user_id=str(user['id']), 
                user_id_type=str(type(user['id'])),
                comment_creator=str(comment.created_by),
                comment_creator_type=str(type(comment.created_by)),
                user_role=user['role'])
                
    if user['role'] not in ['owner', 'admin'] and comment.created_by != user['id']:
        logger.warning("DEBUG COMMENTS: access denied", detail="creator mismatch")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments"
        )
    
    if comment_data.content is not None:
        comment.content = comment_data.content
    
    await db.flush()
    result = await db.execute(select(Comment).where(Comment.id == comment.id))
    return result.scalar_one()


async def delete_comment(db: AsyncSession, user: dict, comment_id: UUID) -> None:
    """Delete a comment"""
    comment = await db.get(Comment, comment_id)
    
    if not comment or comment.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    if comment.tenant_id != user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only owner or comment author can delete
    if user['role'] not in ['owner', 'admin'] and comment.created_by != user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )
    
    await db.delete(comment)
