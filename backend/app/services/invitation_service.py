from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models import InvitationModel
from app.models import Invitation


class InvitationService:
    """Service for invitation operations using SQLAlchemy ORM"""
    
    async def create_invitation(
        self,
        db: AsyncSession,
        tenant_id: int,
        email: str,
        role: str,
        invitation_token: str,
        invited_by: Optional[int] = None,
        expires_in_days: int = 7
    ) -> Invitation:
        """
        Create a new invitation
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            email: Invitee email
            role: Assigned role (admin, manager, member)
            invitation_token: Secure invitation token
            invited_by: User ID who created the invitation (None for CLI)
            expires_in_days: Days until invitation expires
            
        Returns:
            Created Invitation
        """
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        invitation = InvitationModel(
            tenant_id=tenant_id,
            email=email.lower(),
            role=role,
            invitation_token=invitation_token,
            invited_by=invited_by,
            expires_at=expires_at
        )
        
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        
        return self._model_to_pydantic(invitation)
    
    async def get_invitation_by_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[Invitation]:
        """
        Get invitation by token
        
        Args:
            db: Database session
            token: Invitation token
            
        Returns:
            Invitation if found and valid, None otherwise
        """
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.invitation_token == token)
            .where(InvitationModel.accepted_at.is_(None))  # Not already accepted
        )
        invitation_model = result.scalar_one_or_none()
        
        if not invitation_model:
            return None
        
        return self._model_to_pydantic(invitation_model)
    
    async def get_pending_invitations(
        self,
        db: AsyncSession,
        tenant_id: int
    ) -> List[Invitation]:
        """
        Get all pending invitations for a tenant
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            
        Returns:
            List of pending invitations
        """
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant_id)
            .where(InvitationModel.accepted_at.is_(None))
            .where(InvitationModel.expires_at > datetime.utcnow())
            .order_by(InvitationModel.created_at.desc())
        )
        invitation_models = result.scalars().all()
        
        return [self._model_to_pydantic(inv) for inv in invitation_models]
    
    async def accept_invitation(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[Invitation]:
        """
        Mark invitation as accepted
        
        Args:
            db: Database session
            token: Invitation token
            
        Returns:
            Accepted invitation or None if not found
        """
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.invitation_token == token)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            return None
        
        invitation.accepted_at = datetime.utcnow()
        await db.commit()
        await db.refresh(invitation)
        
        return self._model_to_pydantic(invitation)
    
    async def delete_invitation(
        self,
        db: AsyncSession,
        invitation_id: int
    ):
        """
        Delete an invitation
        
        Args:
            db: Database session
            invitation_id: Invitation ID
        """
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if invitation:
            await db.delete(invitation)
            await db.commit()
    
    async def cleanup_expired_invitations(
        self,
        db: AsyncSession
    ) -> int:
        """
        Delete expired invitations
        
        Args:
            db: Database session
            
        Returns:
            Number of deleted invitations
        """
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.expires_at < datetime.utcnow())
            .where(InvitationModel.accepted_at.is_(None))
        )
        expired_invitations = result.scalars().all()
        
        count = len(expired_invitations)
        for invitation in expired_invitations:
            await db.delete(invitation)
        
        await db.commit()
        return count
    
    def _model_to_pydantic(self, model: InvitationModel) -> Invitation:
        """Convert SQLAlchemy model to Pydantic model"""
        return Invitation(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            role=model.role,
            invitation_token=model.invitation_token,
            invited_by=model.invited_by,
            expires_at=model.expires_at,
            accepted_at=model.accepted_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


# Global invitation service instance
invitation_service = InvitationService()
