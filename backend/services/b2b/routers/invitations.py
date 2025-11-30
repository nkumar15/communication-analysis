from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
from uuid import UUID
import secrets

from core.database import get_db
from core.middleware import get_current_user, get_current_active_user
from services.b2b.rbac import require_permission
from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.user_service import user_service
from services.b2b.schemas import Invitation
from core.email import email_service
from core.config import settings


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
    current_user: dict = Depends(get_current_active_user),
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
    from services.b2b.rbac import has_permission
    
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
    
    # RBAC: Check what roles the current user can invite
    current_user_role = current_user.get('role')  # Role slug from current_user
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
    
    return InviteUserResponse(
        invitation_id=invitation.id,
        email=invitation.email,
        status="sent",
        message=f"Invitation sent to {request.email}"
    )


@router.get("/list", response_model=List[InvitationListResponse])
async def list_invitations(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all invitations for current tenant
    
    - Requires admin role
    - Shows pending and accepted invitations
    """
    from services.b2b.models import InvitationModel
    
    # Check admin role
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view invitations"
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
    
    - Requires admin role
    - Only pending invitations can be cancelled
    """
    from services.b2b.models import InvitationModel
    
    # Check admin role
    if current_user.get('role') != 'admin':
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
    await db.commit()
    
    return {"message": "Invitation cancelled successfully"}


@router.post("/resend/{invitation_id}")
async def resend_invitation(
    invitation_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend invitation email
    
    - Requires admin role
    - Only pending, non-expired invitations
    """
    from services.b2b.models import InvitationModel
    
    # Check admin role
    if current_user.get('role') != 'admin':
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
    # Update invitation as accepted
    invitation.accepted_at = datetime.now(timezone.utc)
    invitation.accepted_by = user_id
    invitation.accepted_from_ip = client_ip
    await db.commit()
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": invitation.tenant_id,
        "role": invitation.role
    }
