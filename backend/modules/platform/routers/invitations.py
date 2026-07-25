from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
import secrets

from core.db.session import get_db
from modules.platform.middleware.platform_auth import verify_platform_admin, RequirePlatformPermission
from modules.platform.models import PlatformInvitation, InvitationStatus, PlatformRole

router = APIRouter(
    prefix="/invitations",
    tags=["platform-invitations"]
)

# Schemas
class InviteRequest(BaseModel):
    email: EmailStr
    role_id: UUID

class InviteResponse(BaseModel):
    id: UUID
    email: str
    token: str
    status: str
    expires_at: datetime
    role_name: str

class PublicInviteInfo(BaseModel):
    email: str
    role_name: str
    is_valid: bool

# Endpoints
@router.post("/", response_model=InviteResponse)
async def invite_user(
    req: InviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(RequirePlatformPermission("invitations", "write"))
):
    """Invite a new user to the platform"""
    # Verify role exists
    role = await db.get(PlatformRole, req.role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Verify not pending
    stmt = select(PlatformInvitation).where(
        PlatformInvitation.email == req.email,
        PlatformInvitation.status == InvitationStatus.PENDING
    )
    existing = await db.scalar(stmt)
    if existing:
        raise HTTPException(status_code=400, detail="Pending invitation already exists for this email")

    # Create invitation
    token = secrets.token_urlsafe(32)
    invite = PlatformInvitation(
        platform_tenant_id=UUID(current_user["tenant_id"]),
        email=req.email,
        platform_role_id=req.role_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by=UUID(current_user["id"]),
        status=InvitationStatus.PENDING
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    
    # In a real app, send email here via background task
    print(f"📧 [MOCK EMAIL] To: {req.email}, Link: /platform/signup?token={token}")

    return InviteResponse(
        id=invite.id,
        email=invite.email,
        token=invite.token,
        status=invite.status.value,
        expires_at=invite.expires_at,
        role_name=role.name
    )

@router.get("/", response_model=List[InviteResponse])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(RequirePlatformPermission("invitations", "read"))
):
    stmt = select(PlatformInvitation, PlatformRole).join(PlatformRole)
    result = await db.execute(stmt)
    rows = result.all()
    
    out = []
    for invite, role in rows:
        out.append(InviteResponse(
            id=invite.id,
            email=invite.email,
            token=invite.token,
            status=invite.status.value,
            expires_at=invite.expires_at,
            role_name=role.name
        ))
    return out

@router.post("/{invite_id}/revoke")
async def revoke_invitation(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(RequirePlatformPermission("invitations", "write"))
):
    invite = await db.get(PlatformInvitation, invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    invite.status = InvitationStatus.REVOKED
    await db.commit()
    return {"message": "Invitation revoked"}

@router.get("/validate/{token}", response_model=PublicInviteInfo)
async def validate_token(token: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint to validate token before signup UI shown"""
    stmt = select(PlatformInvitation, PlatformRole).join(PlatformRole).where(
        PlatformInvitation.token == token,
        PlatformInvitation.status == InvitationStatus.PENDING,
        PlatformInvitation.expires_at > datetime.now(timezone.utc)
    )
    res = await db.execute(stmt)
    row = res.first()
    
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    invite, role = row
    return PublicInviteInfo(
        email=invite.email,
        role_name=role.display_name,
        is_valid=True
    )
