"""B2C Invitation Service"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta, timezone
import secrets

from services.b2c.models.workspace_invitation import WorkspaceInvitation
from services.b2c.models.workspace import Workspace
from services.b2c.models.workspace_member import WorkspaceMember
from services.b2c.models.user import B2CUser
from services.b2c.services.workspace_service import workspace_service
from core.logging import get_logger
from core.rls import rls_service

logger = get_logger(__name__)


class InvitationService:
    """B2C Workspace Invitation Service"""
    
    INVITATION_EXPIRY_DAYS = 7
    
    def _generate_token(self) -> str:
        """Generate unique invitation token"""
        return secrets.token_urlsafe(32)
    
    async def create_invitation(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        email: str,
        role: str,
        inviter_id: UUID
    ) -> WorkspaceInvitation:
        """
        Create workspace invitation
        
        Validates:
        - Inviter has admin/owner permission
        - User not already a member
        - Email not already invited
        - Workspace member limit not exceeded
        """
        # Verify inviter has permission (admin or owner)
        await workspace_service.verify_workspace_access(
            db, workspace_id, inviter_id, min_role='admin'
        )
        
        # Check if user already exists and is a member
        # Use security definer function to bypass RLS
        from sqlalchemy import text
        user_id_result = await db.execute(
            select(func.b2c.lookup_user_by_email(email))
        )
        existing_user_id = user_id_result.scalar_one_or_none()
        
        if existing_user_id:
            # Check if already a member
            member_result = await db.execute(
                select(WorkspaceMember).where(
                    and_(
                        WorkspaceMember.workspace_id == workspace_id,
                        WorkspaceMember.user_id == existing_user_id
                    )
                )
            )
            if member_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this workspace"
                )
        
        # Check for existing pending invitation (not cancelled, not accepted)
        existing_invite_result = await db.execute(
            select(WorkspaceInvitation).where(
                and_(
                    WorkspaceInvitation.workspace_id == workspace_id,
                    WorkspaceInvitation.email == email,
                    WorkspaceInvitation.accepted_at.is_(None),
                    WorkspaceInvitation.cancelled_at.is_(None),  # Not cancelled
                    WorkspaceInvitation.expires_at > datetime.now(timezone.utc)
                )
            )
        )
        existing_invite = existing_invite_result.scalar_one_or_none()
        
        if existing_invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation already sent to this email"
            )
        
        # Validate role
        valid_roles = ['admin', 'member', 'viewer']
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Create invitation
        invitation = WorkspaceInvitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            invitation_token=self._generate_token(),
            invited_by=inviter_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.INVITATION_EXPIRY_DAYS)
        )
        db.add(invitation)
        await db.flush()
        
        logger.info(
            "invitation_created",
            invitation_id=str(invitation.id),
            workspace_id=str(workspace_id),
            email=email,
            role=role,
            invited_by=str(inviter_id)
        )
        
        return invitation
    
    async def get_invitation_by_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Dict:
        """
        Get invitation details by token
        
        Public endpoint - no auth required
        Returns workspace and inviter info
        """
        from sqlalchemy.orm import selectinload
        
        result = await db.execute(
            select(WorkspaceInvitation)
            .where(
                and_(
                    WorkspaceInvitation.invitation_token == token,
                    WorkspaceInvitation.cancelled_at.is_(None)  # Not cancelled
                )
            )
            .options(
                selectinload(WorkspaceInvitation.workspace),
                selectinload(WorkspaceInvitation.inviter)
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Check if expired
        if invitation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has expired"
            )
        
        # Check if already accepted
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has already been accepted"
            )
        
        return {
            "id": str(invitation.id),
            "workspace": {
                "id": str(invitation.workspace.id),
                "name": invitation.workspace.name,
                "type": invitation.workspace.type.value
            },
            "email": invitation.email,
            "role": invitation.role,
            "inviter": {
                "id": str(invitation.inviter.id),
                "display_name": invitation.inviter.display_name,
                "email": invitation.inviter.email
            },
            "expires_at": invitation.expires_at.isoformat(),
            "created_at": invitation.created_at.isoformat() if invitation.created_at else None
        }
    
    async def accept_invitation(
        self,
        db: AsyncSession,
        token: str,
        user_id: UUID
    ) -> Dict:
        """
        Accept workspace invitation
        
        Validates:
        - Invitation exists and not expired
        - User email matches invitation email
        - User not already a member
        
        Creates workspace membership
        """
        # Get invitation (not cancelled)
        result = await db.execute(
            select(WorkspaceInvitation)
            .where(
                and_(
                    WorkspaceInvitation.invitation_token == token,
                    WorkspaceInvitation.cancelled_at.is_(None)  # Not cancelled
                )
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Check expiry
        if invitation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has expired"
            )
        
        # Check if already accepted
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Invitation has already been accepted"
            )
        
        # Get user and verify email matches
        user_result = await db.execute(
            select(B2CUser).where(B2CUser.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.email != invitation.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invitation email does not match user email"
            )
        
        # Check if already a member
        member_result = await db.execute(
            select(WorkspaceMember).where(
                and_(
                    WorkspaceMember.workspace_id == invitation.workspace_id,
                    WorkspaceMember.user_id == user_id
                )
            )
        )
        if member_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this workspace"
            )
        
        # Add user as member
        member = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=user_id,
            role=invitation.role
        )
        db.add(member)
        
        # Mark invitation as accepted
        invitation.accepted_at = datetime.now(timezone.utc)
        
        await db.flush()
        
        logger.info(
            "invitation_accepted",
            invitation_id=str(invitation.id),
            workspace_id=str(invitation.workspace_id),
            user_id=str(user_id),
            email=invitation.email,
            role=invitation.role
        )
        
        return {
            "workspace_id": str(invitation.workspace_id),
            "role": invitation.role,
            "message": "Successfully joined workspace"
        }
    
    async def cancel_invitation(
        self,
        db: AsyncSession,
        invitation_id: UUID,
        requester_id: UUID
    ):
        """
        Cancel invitation (soft delete)
        
        Only inviter or workspace owner/admin can cancel
        Sets cancelled_at and cancelled_by for audit trail
        """
        # Get invitation (not already cancelled)
        result = await db.execute(
            select(WorkspaceInvitation).where(
                and_(
                    WorkspaceInvitation.id == invitation_id,
                    WorkspaceInvitation.cancelled_at.is_(None)  # Not already cancelled
                )
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found or already cancelled"
            )
        
        # Cannot cancel accepted invitation
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an accepted invitation"
            )
        
        # Verify permission - must be inviter or workspace admin/owner
        if invitation.invited_by != requester_id:
            # Check if requester is workspace admin/owner
            try:
                await workspace_service.verify_workspace_access(
                    db, invitation.workspace_id, requester_id, min_role='admin'
                )
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only inviter or workspace admin can cancel invitation"
                )
        
        # Soft delete
        invitation.cancelled_at = datetime.now(timezone.utc)
        invitation.cancelled_by = requester_id
        await db.flush()
        
        logger.info(
            "invitation_cancelled",
            invitation_id=str(invitation_id),
            workspace_id=str(invitation.workspace_id),
            cancelled_by=str(requester_id)
        )
    
    async def cleanup_expired_invitations(self, db: AsyncSession) -> int:
        """
        Soft delete expired invitations
        
        Utility method for cron job
        Marks expired invitations as cancelled for audit trail
        Returns count of expired invitations
        """
        from sqlalchemy import func, update
        
        result = await db.execute(
            update(WorkspaceInvitation)
            .where(
                and_(
                    WorkspaceInvitation.expires_at < datetime.now(timezone.utc),
                    WorkspaceInvitation.accepted_at.is_(None),
                    WorkspaceInvitation.cancelled_at.is_(None)  # Not already cancelled
                )
            )
            .values(
                cancelled_at=datetime.now(timezone.utc),
                cancelled_by=None  # System cleanup, no user
            )
            .returning(WorkspaceInvitation.id)
        )
        expired_count = len(result.fetchall())
        
        await db.flush()
        
        logger.info("expired_invitations_cleaned", count=expired_count)
        return expired_count


# Singleton instance
invitation_service = InvitationService()
