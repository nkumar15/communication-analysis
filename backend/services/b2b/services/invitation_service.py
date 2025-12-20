from typing import Optional, List
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.b2b.models import InvitationModel, TenantModel, Role
from services.b2b.schemas import Invitation
from core.utils import get_utc_now
import secrets  # For timing-attack resistant comparison


class InvitationService:
    """Service for invitation operations using SQLAlchemy ORM"""
    
    async def create_invitation(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        role: str,
        invitation_token: str,
        invited_by: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
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
        expires_at = get_utc_now() + timedelta(days=expires_in_days)
        
        invitation = InvitationModel(
            tenant_id=tenant_id,
            email=email.lower(),
            role=role,
            invitation_token=invitation_token,
            invited_by=invited_by,
            team_id=team_id,
            expires_at=expires_at
        )
        
        db.add(invitation)
        # Flush and re-query with RLS context (router handles commit)
        await db.flush()
        result = await db.execute(select(InvitationModel).where(InvitationModel.id == invitation.id))
        invitation = result.scalar_one()
        
        return self._model_to_pydantic(invitation)
    
    async def get_invitation_by_token(
        self,
        db: AsyncSession,
        token: str
    ) -> Optional[Invitation]:
        """
        Get invitation by token with timing-attack resistant comparison
        
        Args:
            db: Database session
            token: Invitation token
            
        Returns:
            Invitation if found and valid, None otherwise
        """
        # Fetch all pending invitations to prevent timing attacks
        # In a high-scale system, consider using a hash-based lookup
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.accepted_at.is_(None))  # Not already accepted
        )
        invitations = result.scalars().all()
        
        # Use constant-time comparison to prevent timing attacks
        for invitation_model in invitations:
            if secrets.compare_digest(invitation_model.invitation_token, token):
                return self._model_to_pydantic(invitation_model)
        
        return None
    
    async def get_pending_invitations(
        self,
        db: AsyncSession,
        tenant_id: UUID
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
            .where(InvitationModel.expires_at > get_utc_now())
            .order_by(InvitationModel.created_at.desc())
        )
        invitation_models = result.scalars().all()
        
        return [self._model_to_pydantic(inv) for inv in invitation_models]
    
    async def accept_invitation(
        self,
        db: AsyncSession,
        token: str,
        accepted_by_user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> Optional[Invitation]:
        """
        Mark invitation as accepted with audit trail
        
        Args:
            db: Database session
            token: Invitation token
            accepted_by_user_id: User ID who accepted (for audit)
            ip_address: IP address of acceptance (for audit)
            
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
        
        invitation.accepted_at = get_utc_now()
        invitation.accepted_by = accepted_by_user_id
        invitation.accepted_from_ip = ip_address
        # Flush and re-query with RLS context (router handles commit)
        await db.flush()
        result = await db.execute(select(InvitationModel).where(InvitationModel.id == invitation.id))
        invitation = result.scalar_one()
        
        return self._model_to_pydantic(invitation)
    
    async def delete_invitation(
        self,
        db: AsyncSession,
        invitation_id: UUID
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
            await db.delete(invitation)
            await db.flush()
    
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
            .where(InvitationModel.expires_at < datetime.now(timezone.utc))
            .where(InvitationModel.accepted_at.is_(None))
        )
        expired_invitations = result.scalars().all()
        
        count = len(expired_invitations)
        for invitation in expired_invitations:
            await db.delete(invitation)
        
        await db.flush()
        return count
    
    async def invite_user_to_tenant(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        role: str,
        invited_by_user_id: UUID,
        current_user_role: str,
        team_id: Optional[UUID] = None,
        team_role: Optional[str] = None
    ) -> tuple[InvitationModel, str]:
        """
        Create invitation with full validation
        
        Returns:
            Tuple of (invitation_model, invitation_token)
        """
        from fastapi import HTTPException, status
        from services.b2b.models import UserModel, Team
        from services.b2b.services.tenant_service import tenant_service
        from core.constants import B2BRoleName
        import secrets
        from datetime import timedelta
        
        # Get tenant
        tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Validate email domain
        email_domain = email.lower().split('@')[1]
        if email_domain != tenant.domain.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email domain must match tenant domain ({tenant.domain})"
            )
        
        # Validate team if provided
        if team_id:
            team_result = await db.execute(
                select(Team).where(
                    Team.id == team_id,
                    Team.tenant_id == tenant_id,
                    Team.deleted_at.is_(None)
                )
            )
            team = team_result.scalar_one_or_none()
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )
        
        # Validate role
        valid_roles = [B2BRoleName.OWNER, B2BRoleName.ADMIN, B2BRoleName.MEMBER, B2BRoleName.VIEWER]
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {role}"
            )
        
        # Role hierarchy validation
        if current_user_role == B2BRoleName.ADMIN and role == B2BRoleName.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot invite Owners"
            )
        
        # Check for existing user
        existing_user_result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant_id)
            .where(UserModel.email == email.lower())
        )
        if existing_user_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists in this tenant"
            )
        
        # Check for pending invitation
        existing_inv_result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant_id)
            .where(InvitationModel.email == email.lower())
            .where(InvitationModel.accepted_at.is_(None))
        )
        if existing_inv_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending invitation already exists for this email"
            )
        
        # Generate token and create invitation
        invitation_token = secrets.token_urlsafe(32)
        invitation = InvitationModel(
            tenant_id=tenant_id,
            email=email.lower(),
            role=role,
            invitation_token=invitation_token,
            invited_by=invited_by_user_id,
            team_id=team_id,
            team_role=team_role,
            expires_at=get_utc_now() + timedelta(days=7)
        )
        
        db.add(invitation)
        await db.flush()
        await db.refresh(invitation)
        
        return invitation, invitation_token
    
    async def list_tenant_invitations(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> List[InvitationModel]:
        """List all invitations for a tenant"""
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant_id)
            .order_by(InvitationModel.created_at.desc())
        )
        return result.scalars().all()
    
    async def cancel_invitation(
        self,
        db: AsyncSession,
        invitation_id: UUID,
        tenant_id: UUID
    ) -> None:
        """
        Cancel a pending invitation with validation
        
        Raises HTTPException if invalid
        """
        from fastapi import HTTPException, status
        
        result = await db.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        if invitation.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot cancel invitation from another tenant"
            )
        
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel accepted invitation"
            )
        
        await db.delete(invitation)
        await db.flush()
    
    async def get_invitation_for_resend(
        self,
        db: AsyncSession,
        invitation_id: UUID,
        tenant_id: UUID
    ) -> InvitationModel:
        """
        Get invitation for resending with validation
        
        Returns invitation if valid for resend
        Raises HTTPException if invalid
        """
        from fastapi import HTTPException, status
        
        result = await db.execute(
            select(InvitationModel).where(InvitationModel.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        if invitation.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot resend invitation from another tenant"
            )
        
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation already accepted"
            )
        
        return invitation
    
    async def validate_invitation_token(
        self,
        db: AsyncSession,
        token: str
    ) -> dict:
        """
        Validate invitation token and return details
        
        Returns dict with tenant info and invitation details
        Raises HTTPException if invalid
        """
        from fastapi import HTTPException, status
        from services.b2b.services.tenant_service import tenant_service
        from services.b2b.services.auth_provider_service import auth_provider_service
        from datetime import datetime, timezone
        
        result = await db.execute(
            select(InvitationModel).where(InvitationModel.invitation_token == token)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invitation"
            )
        
        if invitation.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )
        
        if invitation.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation already accepted"
            )
        
        # Get tenant info
        tenant = await tenant_service.get_tenant_by_id(db, invitation.tenant_id)
        
        # Get primary auth provider
        primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
        
        return {
            "tenant_name": tenant.name,
            "firebase_tenant_id": tenant.firebase_tenant_id,
            "oidc_provider_id": primary_provider.provider_id if primary_provider else None,
            "role": invitation.role,
            "email": invitation.email
        }
    
    async def accept_invitation_and_create_user(
        self,
        db: AsyncSession,
        token: str,
        firebase_uid: str,
        email: str,
        name: Optional[str],
        email_verified: bool,
        user_id_for_audit: Optional[UUID] = None,
        client_ip: Optional[str] = None
    ) -> dict:
        """
        Accept invitation and create/update user
        
        Returns dict with tenant_id, role, team_id, user_id
        Raises HTTPException if validation fails
        """
        from fastapi import HTTPException, status
        from services.b2b.services.tenant_service import tenant_service
        from services.b2b.services.user_service import user_service
        from services.b2b.services import team_service
        from datetime import datetime, timezone
        
        # Get invitation
        result = await db.execute(
            select(InvitationModel).where(InvitationModel.invitation_token == token)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation"
            )
        
        # Enforce email verification
        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email must be verified before accepting invitation. Please verify your email in your authentication provider."
            )
        
        # Verify email match
        if email.lower() != invitation.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email mismatch - invitation is for a different email"
            )
        
        # Get tenant
        tenant = await tenant_service.get_tenant_by_id(db, invitation.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Set tenant context for RLS to ensure we can see roles
        # This is critical because we started in platform_admin context
        from core.rls import rls_service
        await rls_service.set_tenant_context(db, tenant.id)
        
        # Check if user exists
        existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
        
        if not existing_user:
            # Create user
            created_user = await user_service.create_or_update_user(
                db=db,
                tenant_id=tenant.id,
                email=email,
                firebase_uid=firebase_uid,
                name=name,
                role=invitation.role
            )
            user_id = created_user.id
        else:
            user_id = existing_user.id
        
        # Mark invitation as accepted
        invitation.accepted_at = datetime.now(timezone.utc)
        invitation.accepted_by = user_id
        invitation.accepted_from_ip = client_ip
        await db.flush()
        
        # Handle team assignment
        if invitation.team_id:
            try:
                team_role = invitation.team_role if invitation.team_role else "team_contributor"
                await team_service.add_team_member(
                    db=db,
                    team_id=invitation.team_id,
                    user_id=user_id,
                    team_role=team_role
                )
            except Exception:
                pass  # Don't fail if team assignment fails
        else:
            try:
                default_team = await team_service.get_or_create_default_team(
                    db=db,
                    tenant_id=tenant.id
                )
                await team_service.add_team_member(
                    db=db,
                    team_id=default_team.id,
                    user_id=user_id,
                    team_role="team_contributor"
                )
            except Exception:
                pass
        
        return {
            "tenant_id": invitation.tenant_id,
            "role": invitation.role,
            "team_id": invitation.team_id,
            "user_id": user_id
        }
    
    def _model_to_pydantic(self, model: InvitationModel) -> Invitation:
        """Convert SQLAlchemy model to Pydantic model"""
        return Invitation(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            role=model.role,
            invitation_token=model.invitation_token,
            invited_by=model.invited_by,
            team_id=model.team_id,
            expires_at=model.expires_at,
            accepted_at=model.accepted_at,
            accepted_by=model.accepted_by,
            accepted_from_ip=model.accepted_from_ip,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def bulk_create_invitations(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        rows: List,  # List[BulkInviteRow]
        created_by: UUID,
        tenant_domain: str,
        auto_create_teams: bool = True
    ) -> dict:
        """
        Create multiple invitations from bulk upload.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            rows: List of validated BulkInviteRow objects
            created_by: User ID who created bulk invite
            tenant_domain: Tenant's email domain
            auto_create_teams: Whether to auto-create teams if they don't exist
            
        Returns:
            Dict with job_id, results, successful_count, failed_count, teams_created
        """
        from fastapi import HTTPException, status
        from services.b2b.models import Team
        from services.b2b.models.bulk_invite_job import BulkInviteJob
        import secrets
        from datetime import timedelta
        
        results = []
        successful_invitations = []
        failed_count = 0
        teams_created = []
        team_cache = {}  # Cache teams to avoid repeated lookups
        
        # Process each row
        for row in rows:
            try:
                # Get or create team if specified
                team_id = None
                if row.team_name:
                    # Check cache first
                    if row.team_name.lower() in team_cache:
                        team_id = team_cache[row.team_name.lower()]
                    else:
                        # Look up team
                        team_result = await db.execute(
                            select(Team).where(
                                Team.tenant_id == tenant_id,
                                Team.name.ilike(row.team_name),
                                Team.deleted_at.is_(None)
                            )
                        )
                        team = team_result.scalar_one_or_none()
                        
                        if not team and auto_create_teams:
                            # Create team
                            team = Team(
                                tenant_id=tenant_id,
                                name=row.team_name,
                                created_by=created_by
                            )
                            db.add(team)
                            await db.flush()
                            teams_created.append(row.team_name)
                        
                        if team:
                            team_id = team.id
                            team_cache[row.team_name.lower()] = team_id
                
                # Generate token and create invitation
                invitation_token = secrets.token_urlsafe(32)
                invitation = InvitationModel(
                    tenant_id=tenant_id,
                    email=row.email.lower(),
                    role=row.role,
                    invitation_token=invitation_token,
                    invited_by=created_by,
                    team_id=team_id,
                    team_role=row.team_role,
                    expires_at=get_utc_now() + timedelta(days=7)
                )
                
                db.add(invitation)
                await db.flush()
                
                successful_invitations.append(invitation.id)
                
                results.append({
                    "row": row.row_number,
                    "email": row.email,
                    "name": row.name,
                    "role": row.role,
                    "team_name": row.team_name,
                    "status": "success",
                    "invitation_id": str(invitation.id)
                })
                
            except Exception as e:
                failed_count += 1
                results.append({
                    "row": row.row_number,
                    "email": row.email,
                    "status": "error",
                    "error": str(e)
                })
        
        # Create bulk invite job record
        job = BulkInviteJob(
            tenant_id=tenant_id,
            created_by=created_by,
            total_rows=len(rows),
            successful_count=len(successful_invitations),
            failed_count=failed_count,
            results={"rows": results}
        )
        db.add(job)
        await db.flush()
        
        return {
            "job_id": job.id,
            "total_processed": len(rows),
            "successful": len(successful_invitations),
            "failed": failed_count,
            "results": results,
            "teams_created": teams_created,
            "invitation_ids": [str(id) for id in successful_invitations]
        }
    
    async def get_bulk_job(
        self,
        db: AsyncSession,
        job_id: UUID,
        tenant_id: UUID
    ):
        """Get bulk invite job by ID with tenant validation"""
        from fastapi import HTTPException, status
        from services.b2b.models.bulk_invite_job import BulkInviteJob
        
        result = await db.execute(
            select(BulkInviteJob).where(
                BulkInviteJob.id == job_id,
                BulkInviteJob.tenant_id == tenant_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bulk invite job not found"
            )
        
        return job
    
    async def list_bulk_jobs(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        limit: int = 20,
        offset: int = 0
    ):
        """List bulk invite jobs for a tenant"""
        from services.b2b.models.bulk_invite_job import BulkInviteJob
        
        result = await db.execute(
            select(BulkInviteJob)
            .where(BulkInviteJob.tenant_id == tenant_id)
            .order_by(BulkInviteJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


# Global invitation service instance
invitation_service = InvitationService()
