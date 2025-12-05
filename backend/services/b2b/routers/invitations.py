from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from uuid import UUID
import secrets

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.middleware import get_current_active_user
from services.b2b.rbac import require_permission
from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.user_service import user_service
from services.b2b.services.audit_service import log_audit_background
from services.b2b.schemas import Invitation
from core.email import email_service
from core.config import settings
from core.constants import B2BRoleName


router = APIRouter(prefix="/api/b2b/invitations", tags=["invitations"])


from core.constants import B2BRoleName

# Request/Response Models
class InviteUserRequest(BaseModel):
    """Request to invite a new user"""
    email: str
    role: str = B2BRoleName.VIEWER  # Default to viewer (lowest permission)
    team_id: UUID | None = None  # Optional team assignment
    team_role: str | None = None  # Team role if team_id is specified


class InviteUserResponse(BaseModel):
    invitation_id: UUID
    email: str
    status: str
    message: str
    team_id: UUID | None = None


class InvitationListResponse(BaseModel):
    id: UUID
    email: str
    role: str
    invited_by: UUID | None
    team_id: UUID | None
    expires_at: datetime
    accepted_at:datetime | None
    created_at: datetime


@router.post("/invite", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a new user to the tenant
    
    Permission required: users:invite
    
    Role restrictions:
    - Owner: Can invite Owner, Admin, Viewer
    - Admin: Can invite Admin, Viewer
    - Viewer: Cannot invite (no permission)
    """
    from services.b2b.rbac import has_permission
    from services.b2b.models import Team
    
    # Check if user has invite permission
    if not await has_permission(current_user['id'], 'users', 'invite', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Get tenant info for domain validation
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Validate email domain matches tenant domain
    email_domain = request.email.lower().split('@')[1]
    if email_domain != tenant.domain.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email domain must match tenant domain ({tenant.domain})"
        )
    
    # Validate team if provided
    if request.team_id:
        team_result = await db.execute(
            select(Team).where(
                Team.id == request.team_id,
                Team.tenant_id == current_user['tenant_id'],
                Team.deleted_at.is_(None)
            )
        )
        team = team_result.scalar_one_or_none()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
    
    # RBAC: Check what roles the current user can invite
    current_user_role = current_user.get('role')  # Role slug from current_user
    requested_role = request.role
    
    # Validate requested role exists in system
    valid_roles = [B2BRoleName.OWNER, B2BRoleName.ADMIN, B2BRoleName.VIEWER]
    if requested_role not in valid_roles:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {requested_role}"
        )

    # Owner can invite anyone
    if current_user_role == B2BRoleName.OWNER:
        pass # Allowed
        
    # Admin can invite Admin or Viewer (but NOT Owner)
    elif current_user_role == B2BRoleName.ADMIN:
        if requested_role == B2BRoleName.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins cannot invite Owners"
            )
    else:
        # Other roles (like Viewer) should be caught by permission check above, 
        # but as a safety net:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Check if user already exists
    from services.b2b.models import UserModel as ExistingUserModel
    
    existing_user_result = await db.execute(
        select(ExistingUserModel)
        .where(ExistingUserModel.tenant_id == current_user['tenant_id'])
        .where(ExistingUserModel.email == request.email.lower())
    )
    existing_user = existing_user_result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists in this tenant"
        )
    
    # Check if invitation already exists (pending)
    from services.b2b.models import InvitationModel
    
    existing_inv_result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == current_user['tenant_id'])
        .where(InvitationModel.email == request.email.lower())
        .where(InvitationModel.accepted_at.is_(None))
    )
    existing_invitation = existing_inv_result.scalar_one_or_none()
    
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists for this email"
        )
    
    # Generate secure invitation token
    invitation_token = secrets.token_urlsafe(32)
    
    # Create invitation directly
    from services.b2b.models import InvitationModel
    from datetime import timedelta
    
    invitation = InvitationModel(
        tenant_id=current_user['tenant_id'],
        email=request.email,
        role=request.role,
        invitation_token=invitation_token,
        invited_by=current_user['id'],
        team_id=request.team_id,
        team_role=request.team_role,  # NEW: Save team role
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(invitation)
    await db.flush()
    await db.refresh(invitation)
    
    # Send invitation email
    frontend_url = settings.frontend_url or "http://localhost:3000"
    invitation_url = f"{frontend_url}/invite/{invitation_token}"
    
    email_service.send_user_invitation_email(
        to_email=request.email,
        tenant_name=tenant.name,
        inviter_name=current_user.get('name') or current_user['email'],
        role=request.role,
        invitation_url=invitation_url,
        expires_at=invitation.expires_at
    )

    # Log audit event
    background_tasks.add_task(
        log_audit_background,
        tenant_id=current_user['tenant_id'],
        event_type="user.invited",
        resource_type="invitation",
        actor_id=current_user['id'],
        resource_id=invitation.id,
        details={"email": request.email, "role": request.role, "team_id": str(request.team_id) if request.team_id else None},
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("User-Agent")
    )

    return InviteUserResponse(
        invitation_id=invitation.id,
        email=invitation.email,
        status="sent",  
        message=f"Invitation sent to {request.email}",
        team_id=invitation.team_id
    )


@router.get("/list", response_model=List[InvitationListResponse])
async def list_invitations(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all invitations for current tenant
    
    - Requires invitations:read permission
    - Shows pending and accepted invitations
    """
    from services.b2b.models import InvitationModel
    from services.b2b.rbac import has_permission
    
    # Check permission using RBAC
    if not await has_permission(current_user['id'], 'invitations', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view invitations"
        )
    
    result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == current_user['tenant_id'])
        .order_by(InvitationModel.created_at.desc())
    )
    invitations = result.scalars().all()
    
    return [
        InvitationListResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            invited_by=inv.invited_by,
            team_id=inv.team_id,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            created_at=inv.created_at
        )
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel/delete a pending invitation
    
    - Requires invitations:delete permission
    - Only pending invitations can be cancelled
    """
    from services.b2b.models import InvitationModel
    from services.b2b.rbac import has_permission
    
    # Check permission using RBAC
    if not await has_permission(current_user['id'], 'invitations', 'delete', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel invitations"
        )
    
    # Get invitation
    result = await db.execute(
        select(InvitationModel).where(InvitationModel.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check tenant ownership
    if invitation.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel invitation from another tenant"
        )
    
    # Check if already accepted
    if invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel accepted invitation"
        )
    
    # Delete invitation
    await db.delete(invitation)
    await db.delete(invitation)
    # await db.commit() - Handled by dependency
    
    return {"message": "Invitation cancelled successfully"}


@router.post("/resend/{invitation_id}")
async def resend_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend invitation email
    
    - Requires invitations:write permission
    - Only pending, non-expired invitations
    """
    from services.b2b.models import InvitationModel
    from services.b2b.rbac import has_permission
    
    # Check permission using RBAC
    if not await has_permission(current_user['id'], 'invitations', 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to resend invitations"
        )
    
    # Get invitation
    result = await db.execute(
        select(InvitationModel).where(InvitationModel.id == invitation_id)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check tenant ownership
    if invitation.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot resend invitation from another tenant"
        )
    
    # Check if already accepted
    if invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted"
        )
    
    # Get tenant info
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    
    # Resend email
    frontend_url = settings.frontend_url or "http://localhost:3000"
    invitation_url = f"{frontend_url}/invite/{invitation.invitation_token}"
    
    email_service.send_user_invitation_email(
        to_email=invitation.email,
        tenant_name=tenant.name,
        inviter_name=current_user.get('name') or current_user['email'],
        role=invitation.role,
        invitation_url=invitation_url,
        expires_at=invitation.expires_at
    )
    
    return {"message": f"Invitation resent to {invitation.email}"}


@router.get("/accept/{token}")
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate invitation token (public endpoint)
    
    Returns MINIMAL invitation details for display (PII minimization)
    """
    # Get invitation by token
    from services.b2b.models import InvitationModel
    result = await db.execute(
        select(InvitationModel).where(InvitationModel.invitation_token == token)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation"
        )
    
    # Check if expired
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check if already accepted
    if invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already accepted"
        )
    
    # Get tenant info
    tenant = await tenant_service.get_tenant_by_id(db, invitation.tenant_id)
    
    # Get primary auth provider
    from services.b2b.services.auth_provider_service import auth_provider_service
    primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
    
    # Return MINIMAL data to prevent PII leakage
    # Note: tenant_id removed, inviter_name removed
    return {
        "tenant_name": tenant.name,
        "firebase_tenant_id": tenant.firebase_tenant_id,
        "oidc_provider_id":primary_provider.provider_id if primary_provider else None,
        "role": invitation.role,
        "email": invitation.email  # Keep for UI display to user
    }


@router.post("/join")
async def join_tenant(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    decoded_token: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept invitation and join tenant (after SSO login)
    
    - Requires authentication (Firebase token)
    - Enforces EMAIL VERIFICATION (security fix)
    - Creates user from invitation if doesn't exist
    - Marks invitation as accepted with audit trail
    
    This endpoint handles new users who just completed SSO login
    """
    from core.utils.firebase import firebase_auth_service
    
    # Get invitation
    # Get invitation by token
    from services.b2b.models import InvitationModel
    result = await db.execute(
        select(InvitationModel).where(InvitationModel.invitation_token == token)
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation"
        )
    
    # Extract user info from Firebase token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    email_verified = user_info.get("email_verified", False)  # Get email verification status
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # SECURITY: Enforce email verification
    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email must be verified before accepting invitation. Please verify your email in your authentication provider."
        )
    
    # Verify user's email matches invitation
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
    
    # Check if user already exists
    existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    user_id = None
    if not existing_user:
        # Create user from invitation
        created_user = await user_service.create_or_update_user(
            db=db,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=firebase_uid,
            name=name,
            role=invitation.role  # Use role from invitation
        )
        user_id = created_user.id
    else:
        user_id = existing_user.id
    
    # Get client IP for audit trail
    client_ip = request.client.host if request.client else None
    
    # Mark invitation as accepted with audit trail
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_by = user_id
    invitation.accepted_from_ip = client_ip
    
    # Flush, re-query with RLS context (FastAPI commits on success)
    await db.flush()
    result = await db.execute(select(InvitationModel).where(InvitationModel.id == invitation.id))
    invitation = result.scalar_one()
    
    # Handle Team Assignment
    from services.b2b.services import team_service
    
    if invitation.team_id:
        # Add to specific team from invitation
        try:
            # Use team_role from invitation if specified, otherwise default to team_member
            team_role = invitation.team_role if invitation.team_role else "team_member"
            await team_service.add_team_member(
                db=db,
                team_id=invitation.team_id,
                user_id=user_id,
                team_role=team_role
            )
        except Exception as e:
            # Log error but don't fail the join process
            # User is created but team assignment failed
            pass
    else:
        # Add to default team
        try:
            default_team = await team_service.get_or_create_default_team(
                db=db,
                tenant_id=tenant.id
            )
            await team_service.add_team_member(
                db=db,
                team_id=default_team.id,
                user_id=user_id,
                team_role="team_member"
            )
        except Exception as e:
            pass

    # await db.commit() - Handled by dependency

    # Log audit event
    background_tasks.add_task(
        log_audit_background,
        tenant_id=tenant.id,
        event_type="user.accepted_invite",
        resource_type="invitation",
        actor_id=user_id,
        resource_id=invitation.id,
        details={"email": email, "role": invitation.role},
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": invitation.tenant_id,
        "role": invitation.role,
        "team_id": invitation.team_id
    }
