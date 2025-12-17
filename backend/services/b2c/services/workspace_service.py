"""B2C Workspace Service"""
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from uuid import UUID, uuid4

from services.b2c.models.workspace import Workspace, WorkspaceType
from services.b2c.models.workspace_member import WorkspaceMember
from services.b2c.models.user import B2CUser
from services.b2c.services.quota_service import quota_service
from core.logging import get_logger
from core.rls import rls_service

logger = get_logger(__name__)


class WorkspaceService:
    """B2C Workspace Management Service"""
    
    async def create_team_workspace(
        self,
        db: AsyncSession,
        name: str,
        owner_id: UUID,
        subscription_tier: str = 'free'
    ) -> Workspace:
        """
        Create a new team workspace
        
        Validates:
        - Owner has active subscription (Premium+ required for team workspaces)
        - Owner hasn't exceeded workspace quota
        
        Creates:
        - Workspace record
        - Owner membership
        """
        # Check workspace quota
        can_create, limit_info = await quota_service.check_team_workspace_limit(
            db, str(owner_id), subscription_tier
        )
        if not can_create:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Workspace limit reached. {limit_info}"
            )
        
        # Create workspace
        workspace = Workspace(
            name=name,
            type=WorkspaceType.team,
            owner_id=owner_id,
            subscription_tier=subscription_tier
        )
        db.add(workspace)
        await db.flush()
        
        # Add owner as member
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role='owner'
        )
        db.add(member)
        await db.flush()
        
        logger.info(
            "team_workspace_created",
            workspace_id=str(workspace.id),
            owner_id=str(owner_id),
            name=name
        )
        
        return workspace
    
    async def get_workspace_details(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID
    ) -> Dict:
        """
        Get workspace details with members
        
        Verifies user has access to workspace via RLS
        """
        # Set RLS context
        await rls_service.set_user_context(db, str(user_id))
        
        # Get workspace with members
        result = await db.execute(
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.subscription))
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied"
            )
        
        # Get members
        members_result = await db.execute(
            select(WorkspaceMember, B2CUser)
            .join(B2CUser, WorkspaceMember.user_id == B2CUser.id)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        members_data = members_result.all()
        
        members = []
        for member_rel, user in members_data:
            members.append({
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "role": member_rel.role,
                "joined_at": member_rel.joined_at.isoformat() if member_rel.joined_at else None
            })
        
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "type": workspace.type.value,
            "owner_id": str(workspace.owner_id),
            "subscription_tier": workspace.subscription_tier,
            "settings": workspace.settings,
            "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
            "members": members,
            "member_count": len(members)
        }
    
    async def update_workspace_settings(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> Workspace:
        """
        Update workspace settings
        
        Only owner or admin can update
        """
        # Verify permission (owner or admin)
        await self.verify_workspace_access(
            db, workspace_id, user_id, min_role='admin'
        )
        
        # Get workspace
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Update fields
        if name is not None:
            workspace.name = name
        if settings is not None:
            workspace.settings = settings
        
        await db.flush()
        
        logger.info(
            "workspace_updated",
            workspace_id=str(workspace_id),
            updated_by=str(user_id)
        )
        
        return workspace
    
    async def delete_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID
    ):
        """
        Delete workspace
        
        Only owner can delete
        Cascades to members and all workspace data
        """
        # Verify owner permission
        await self.verify_workspace_access(
            db, workspace_id, user_id, min_role='owner'
        )
        
        # Get workspace
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # Prevent deletion of personal workspace
        if workspace.type == WorkspaceType.personal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete personal workspace"
            )
        
        await db.delete(workspace)
        await db.flush()
        
        logger.info(
            "workspace_deleted",
            workspace_id=str(workspace_id),
            deleted_by=str(user_id)
        )
    
    async def update_member_role(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        target_user_id: UUID,
        new_role: str,
        requester_id: UUID
    ):
        """
        Update workspace member role
        
        Only owner or admin can update roles
        Owner cannot be demoted
        """
        # Verify permission
        await self.verify_workspace_access(
            db, workspace_id, requester_id, min_role='admin'
        )
        
        # Get member
        result = await db.execute(
            select(WorkspaceMember).where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == target_user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in workspace"
            )
        
        # Prevent owner demotion
        if member.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change owner role. Transfer ownership first."
            )
        
        # Validate new role
        valid_roles = ['admin', 'member', 'viewer']
        if new_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        member.role = new_role
        await db.flush()
        
        logger.info(
            "member_role_updated",
            workspace_id=str(workspace_id),
            user_id=str(target_user_id),
            new_role=new_role,
            updated_by=str(requester_id)
        )
    
    async def remove_member(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        target_user_id: UUID,
        requester_id: UUID
    ):
        """
        Remove member from workspace
        
        Only owner or admin can remove members
        Cannot remove owner
        """
        # Verify permission
        await self.verify_workspace_access(
            db, workspace_id, requester_id, min_role='admin'
        )
        
        # Get member
        result = await db.execute(
            select(WorkspaceMember).where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == target_user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in workspace"
            )
        
        # Prevent owner removal
        if member.role == 'owner':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove workspace owner"
            )
        
        await db.delete(member)
        await db.flush()
        
        logger.info(
            "member_removed",
            workspace_id=str(workspace_id),
            user_id=str(target_user_id),
            removed_by=str(requester_id)
        )
    
    async def verify_workspace_access(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        min_role: str = 'member'
    ) -> bool:
        """
        Verify user has required role in workspace
        
        Role hierarchy: owner > admin > member > viewer
        """
        role_hierarchy = {
            'viewer': 0,
            'member': 1,
            'admin': 2,
            'owner': 3
        }
        
        # Get user's role in workspace
        result = await db.execute(
            select(WorkspaceMember).where(
                and_(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - not a workspace member"
            )
        
        # Check role hierarchy
        user_role_level = role_hierarchy.get(member.role, 0)
        required_role_level = role_hierarchy.get(min_role, 0)
        
        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied - {min_role} role required"
            )
        
        return True


# Singleton instance
workspace_service = WorkspaceService()
