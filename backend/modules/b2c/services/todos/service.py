from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException, status

from modules.b2c.services.todos.models import B2CTodo
from modules.b2c.services.workspace_service import WorkspaceService

class TodoService:
    def __init__(self):
        self.workspace_service = WorkspaceService()

    async def create_todo(
        self, 
        db: AsyncSession, 
        workspace_id: UUID, 
        user_id: UUID, 
        data: dict
    ) -> B2CTodo:
        """Create a new todo item in the workspace"""
        # Ensure user has access to workspace (WRITE access)
        # Note: RLS handles data visibility, but we check permissions for operations
        await self.workspace_service.verify_workspace_access(db, workspace_id, user_id, 'member')
        
        todo = B2CTodo(
            workspace_id=workspace_id,
            title=data['title'],
            description=data.get('description'),
            due_date=data.get('due_date'),
            created_by=user_id
        )
        db.add(todo)
        await db.flush()
        await db.refresh(todo)
        return todo

    async def list_todos(
        self, 
        db: AsyncSession, 
        workspace_id: UUID, 
        user_id: UUID
    ) -> list[B2CTodo]:
        """List all todos in a workspace (filtered by RLS)"""
        # Check basic read access
        await self.workspace_service.verify_workspace_access(db, workspace_id, user_id, 'viewer')
        
        result = await db.execute(
            select(B2CTodo)
            .where(B2CTodo.workspace_id == workspace_id)
            .order_by(desc(B2CTodo.created_at))
        )
        return result.scalars().all()

    async def update_todo(
        self, 
        db: AsyncSession, 
        workspace_id: UUID, 
        todo_id: UUID, 
        user_id: UUID, 
        data: dict
    ) -> B2CTodo:
        """Update a todo item"""
        await self.workspace_service.verify_workspace_access(db, workspace_id, user_id, 'member')
        
        result = await db.execute(
            select(B2CTodo).where(
                B2CTodo.id == todo_id,
                B2CTodo.workspace_id == workspace_id
            )
        )
        todo = result.scalar_one_or_none()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
            
        for key, value in data.items():
            if hasattr(todo, key):
                setattr(todo, key, value)
                
        await db.flush()
        await db.refresh(todo)
        return todo

    async def delete_todo(
        self, 
        db: AsyncSession, 
        workspace_id: UUID, 
        todo_id: UUID, 
        user_id: UUID
    ):
        """Delete a todo item"""
        await self.workspace_service.verify_workspace_access(db, workspace_id, user_id, 'member')
        
        result = await db.execute(
            select(B2CTodo).where(
                B2CTodo.id == todo_id,
                B2CTodo.workspace_id == workspace_id
            )
        )
        todo = result.scalar_one_or_none()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
            
        await db.delete(todo)
        await db.flush()

todo_service = TodoService()
