"""
Invitations API Router

Handles user invitation creation, validation, and acceptance.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.middleware import get_current_active_user
from services.b2b.services.invitation_service import invitation_service
from services.b2b.services.tenant_service import tenant_service
from services.b2b.schemas.invitation import (
    InviteUserRequest,
    InviteUserResponse,
    InvitationListResponse
)
from services.b2b.rbac import has_permission
from core.email import email_service
from core.config import settings
from core.rls import rls_service


router = APIRouter(prefix="/api/b2b/invitations", tags=["invitations"])


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
    # Check permission
    if not await has_permission(current_user['id'], 'users', 'invite', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite users"
        )
    
    # Create invitation via service
    invitation, invitation_token = await invitation_service.invite_user_to_tenant(
        db=db,
        tenant_id=current_user['tenant_id'],
        email=request.email,
        role=request.role,
        invited_by_user_id=current_user['id'],
        current_user_role=current_user.get('role'),
        team_id=request.team_id,
        team_role=request.team_role
    )
    
    # Get tenant for email
    tenant = await tenant_service.get_tenant_by_id(db, current_user['tenant_id'])
    
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
    from services.b2b.services.audit_service import AuditService
    audit_service = AuditService(db)
    
    await audit_service.log_event(
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
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view invitations"
        )
    
    invitations = await invitation_service.list_tenant_invitations(
        db=db,
        tenant_id=current_user['tenant_id']
    )
    
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
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'delete', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel invitations"
        )
    
    await invitation_service.cancel_invitation(
        db=db,
        invitation_id=invitation_id,
        tenant_id=current_user['tenant_id']
    )
    
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
    # Check permission
    if not await has_permission(current_user['id'], 'invitations', 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to resend invitations"
        )
    
    # Get and validate invitation
    invitation = await invitation_service.get_invitation_for_resend(
        db=db,
        invitation_id=invitation_id,
        tenant_id=current_user['tenant_id']
    )
    
    # Get tenant for email
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
    # Bypass RLS - token is the security key
    await rls_service.set_platform_admin_context(db)
    
    result = await invitation_service.validate_invitation_token(db=db, token=token)
    
    return result


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
    
    # Bypass RLS to find invitation globally
    await rls_service.set_platform_admin_context(db)
    
    # Extract user info from Firebase token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    email_verified = user_info.get("email_verified", False)
    
    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Accept invitation and create user (service handles RLS context switch)
    result = await invitation_service.accept_invitation_and_create_user(
        db=db,
        token=token,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
        email_verified=email_verified,
        client_ip=request.client.host if request.client else None
    )
    
    # Switch to invitation's tenant context for audit log
    await rls_service.set_tenant_context(db, result['tenant_id'])
    
    # Log audit event
    from services.b2b.services.audit_service import AuditService
    audit_service = AuditService(db)
    
    await audit_service.log_event(
        tenant_id=result['tenant_id'],
        event_type="user.accepted_invite",
        resource_type="invitation",
        actor_id=result['user_id'],
        resource_id=None,  # Invitation ID not returned
        details={"email": email, "role": result['role']},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {
        "message": "Successfully joined tenant",
        "tenant_id": result['tenant_id'],
        "role": result['role'],
        "team_id": result['team_id']
    }
