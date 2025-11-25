from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from uuid import UUID
import secrets

from app.database import get_db
from app.services.invitation_service import invitation_service
from app.services.tenant_service import tenant_service
from app.services.user_service import user_service
from app.middleware.auth import get_current_user
from app.models import Invitation
from cli.email_service import email_service
from app.config import settings


router = APIRouter(prefix="/api/invitations", tags=["invitations"])


# Request/Response Models
class InviteUserRequest(BaseModel):
    """Request to invite a new user"""
    email: str
    role: str = 'field_agent'  # Default to field_agent (lowest permission)


class InviteUserResponse(BaseModel):
    invitation_id: UUID
    email: str
    status: str
    message: str


class InvitationListResponse(BaseModel):
    id: UUID
    email: str
    role: str
    invited_by: UUID | None
    expires_at: datetime
    accepted_at:datetime | None
    created_at: datetime


@router.post("/invite", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a new user to the tenant
    
    Permission required: users:invite
    
    Role restrictions:
    - Admin: Can invite admin, field_manager, field_agent
    - Field Manager: Can only invite field_agent
    - Field Agent: Cannot invite (no permission)
    """
    from app.rbac import has_permission
    
    # Check if user has invite permission
    if not await has_permission(current_user['id'], 'users', 'invite', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Get current user's details
    from app.db_models import UserModel
    
    result = await db.execute(
        select(UserModel).where(UserModel.firebase_uid == current_user.get("uid"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Admin check removed here to allow field_managers (logic handled below)
    # if user.role != 'admin':
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Only admins can invite users"
    #     )
    
    # Get tenant info for domain validation
    tenant = await tenant_service.get_tenant_by_id(db, user.tenant_id)
    
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
    
    # RBAC: Check what roles the current user can invite
    from app.rbac import get_user_role_name
    
    current_user_role = await get_user_role_name(user.id, db)
    requested_role = request.role
    
    # Admin can invite anyone
    # Field Manager can only invite field_agent (NOT other field_managers)
    # Field Agent cannot invite anyone (should not reach here due to permission check)
    if current_user_role == 'field_manager':
        if requested_role != 'field_agent':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Field managers can only invite field agents"
            )
    elif current_user_role == 'admin':
        # Admin can invite admin, field_manager, or field_agent
        if requested_role not in ['admin', 'field_manager', 'field_agent']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {requested_role}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Check if user already exists
    from app.db_models import UserModel as ExistingUserModel
    
    existing_user_result = await db.execute(
        select(ExistingUserModel)
        .where(ExistingUserModel.tenant_id == user.tenant_id)
        .where(ExistingUserModel.email == request.email.lower())
    )
    existing_user = existing_user_result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists in this tenant"
        )
    
    # Check if invitation already exists (pending)
    from app.db_models import InvitationModel
    
    existing_inv_result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == user.tenant_id)
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
    
    # Create invitation
    invitation = await invitation_service.create_invitation(
        db=db,
        tenant_id=user.tenant_id,
        email=request.email,
        role=request.role,
        invitation_token=invitation_token,
        invited_by=user.id,
        expires_in_days=7
    )
    
    # Send invitation email
    frontend_url = settings.frontend_url or "http://localhost:3000"
    invitation_url = f"{frontend_url}/invite/{invitation_token}"
    
    email_service.send_user_invitation_email(
        to_email=request.email,
        tenant_name=tenant.name,
        inviter_name=user.name or user.email,
        role=request.role,
        invitation_url=invitation_url,
        expires_at=invitation.expires_at
    )
    
    return InviteUserResponse(
        invitation_id=invitation.id,
        email=invitation.email,
        status="sent",
        message=f"Invitation sent to {request.email}"
    )


@router.get("/list", response_model=List[InvitationListResponse])
async def list_invitations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all invitations for current tenant
    
    - Requires admin role
    - Shows pending and accepted invitations
    """
    from app.db_models import UserModel, InvitationModel
    from app.rbac_models import Role
    
    # Get current user with role
    result = await db.execute(
        select(UserModel, Role)
        .join(Role, UserModel.role_id == Role.id)
        .where(UserModel.firebase_uid == current_user.get("uid"))
    )
    user_row = result.first()
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    user_obj, role_obj = user_row
    # Check admin role
    if role_obj is None or role_obj.name != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view invitations"
        )
    # Use user_obj for tenant_id
    user = user_obj
    
    result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == user.tenant_id)
        .order_by(InvitationModel.created_at.desc())
    )
    invitations = result.scalars().all()
    
    return [
        InvitationListResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            invited_by=inv.invited_by,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at,
            created_at=inv.created_at
        )
        for inv in invitations
    ]


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel/delete a pending invitation
    
    - Requires admin role
    - Only pending invitations can be cancelled
    """
    from app.db_models import UserModel, InvitationModel
    
    # Get current user
    result = await db.execute(
        select(UserModel).where(UserModel.firebase_uid == current_user.get("uid"))
    )
    user = result.scalar_one_or_none()
    
    if not user or user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can cancel invitations"
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
    if invitation.tenant_id != user.tenant_id:
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
    await invitation_service.delete_invitation(db, invitation_id)
    
    return {"message": "Invitation cancelled successfully"}


@router.post("/resend/{invitation_id}")
async def resend_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend invitation email
    
    - Requires admin role
    - Only pending, non-expired invitations
    """
    from app.db_models import UserModel, InvitationModel
    
    # Get current user
    result = await db.execute(
        select(UserModel).where(UserModel.firebase_uid == current_user.get("uid"))
    )
    user = result.scalar_one_or_none()
    
    if not user or user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can resend invitations"
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
    if invitation.tenant_id != user.tenant_id:
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
    tenant = await tenant_service.get_tenant_by_id(db, user.tenant_id)
    
    # Resend email
    frontend_url = settings.frontend_url or "http://localhost:3000"
    invitation_url = f"{frontend_url}/invite/{invitation.invitation_token}"
    
    email_service.send_user_invitation_email(
        to_email=invitation.email,
        tenant_name=tenant.name,
        inviter_name=user.name or user.email,
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
    
    Returns invitation details for display
    """
    invitation = await invitation_service.get_invitation_by_token(db, token)
    
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
    
    # Get inviter info if exists
    inviter_name = "Admin"
    if invitation.invited_by:
        inviter = await user_service.get_user_by_id(db, invitation.invited_by)
        if inviter:
            inviter_name = inviter.name or inviter.email
    
    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "firebase_tenant_id": tenant.firebase_tenant_id,
        "oidc_provider_id": tenant.oidc_provider_id,
        "inviter_name": inviter_name,
        "role": invitation.role,
        "email": invitation.email
    }


@router.post("/join")
async def join_tenant(
    token: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept invitation and join tenant (after SSO login)
    
    - Requires authentication
    - Validates invitation
    - Marks invitation as accepted
    """
    # Get invitation
    invitation = await invitation_service.get_invitation_by_token(db, token)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation"
        )
    
    # Verify user's email matches invitation
    user_email = current_user.get("email")
    if user_email.lower() != invitation.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email mismatch - invitation is for a different email"
        )
    
    # Mark invitation as accepted
    await invitation_service.accept_invitation(db, token)
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": invitation.tenant_id,
        "role": invitation.role
    }
