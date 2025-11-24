from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.services.user_service import user_service
from app.middleware.auth import get_current_user
from app.db_models import UserModel, InvitationModel


router = APIRouter(prefix="/api/users", tags=["users"])


# Response Models
class UserResponse(BaseModel):
    id: int
    name: str | None
    email: str
    role: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime


class StatsResponse(BaseModel):
    total_users: int
    active_users: int
    pending_invitations: int
    managers_count: int


@router.get("/stats", response_model=StatsResponse)
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user and invitation statistics for current tenant
    
    - Requires authentication
    - Returns counts for dashboard stats
    """
    from app.db_models import UserModel as CurrentUserModel
    
    # Get current user's tenant
    result = await db.execute(
        select(CurrentUserModel).where(CurrentUserModel.firebase_uid == current_user.get("uid"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    tenant_id = user.tenant_id
    
    # Get total users count
    total_result = await db.execute(
        select(func.count(UserModel.id))
        .where(UserModel.tenant_id == tenant_id)
    )
    total_users = total_result.scalar()
    
    # Get active users count
    active_result = await db.execute(
        select(func.count(UserModel.id))
        .where(UserModel.tenant_id == tenant_id)
        .where(UserModel.is_active == True)
    )
    active_users = active_result.scalar()
    
    # Get pending invitations count
    pending_result = await db.execute(
        select(func.count(InvitationModel.id))
        .where(InvitationModel.tenant_id == tenant_id)
        .where(InvitationModel.accepted_at.is_(None))
    )
    pending_invitations = pending_result.scalar()
    
    # Get managers count
    managers_result = await db.execute(
        select(func.count(UserModel.id))
        .where(UserModel.tenant_id == tenant_id)
        .where(UserModel.role == 'manager')
    )
    managers_count = managers_result.scalar()
    
    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        pending_invitations=pending_invitations,
        managers_count=managers_count
    )


@router.get("/list", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in current tenant
    
    - Requires authentication
    - Returns all users with their details
    """
    from app.db_models import UserModel as CurrentUserModel
    
    # Get current user's tenant
    result = await db.execute(
        select(CurrentUserModel).where(CurrentUserModel.firebase_uid == current_user.get("uid"))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Get all users in tenant
    users_result = await db.execute(
        select(UserModel)
        .where(UserModel.tenant_id == user.tenant_id)
        .order_by(UserModel.created_at.desc())
    )
    users = users_result.scalars().all()
    
    return [
        UserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            last_login=u.last_login,
            created_at=u.created_at
        )
        for u in users
    ]
