from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.db_models import UserModel, InvitationModel
from app.rbac_models import Role
from app.middleware.auth import get_current_active_user, get_current_user
from app.database import get_db

# Placeholder block removed - moved logic into list_users endpoint



router = APIRouter(prefix="/api/users", tags=["users"])


# Response Models
class UserResponse(BaseModel):
    id: UUID
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
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user and invitation statistics for current tenant (scoped by role)
    
    - Requires authentication
    - Returns counts scoped to user's access level:
      - Admin: All users in tenant
      - Field Manager: Users in their team
      - Field Agent: N/A (no dashboard access)
    """
    from app.rbac import get_dashboard_stats, require_permission
    
    # Check if user has dashboard access (admin and field_manager only)
    # This will raise 403 if user doesn't have permission
    from app.rbac.permission_checker import has_permission
    if not await has_permission(current_user['id'], 'dashboard', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dashboard access denied. Field agents cannot access dashboard."
        )
    
    # Get scoped stats based on user's role and hierarchy
    stats = await get_dashboard_stats(current_user['id'], db)
    
    # Get pending invitations count (scoped to tenant for now)
    pending_result = await db.execute(
        select(func.count(InvitationModel.id))
        .where(InvitationModel.tenant_id == current_user['tenant_id'])
        .where(InvitationModel.accepted_at.is_(None))
    )
    pending_invitations = pending_result.scalar()
    
    return StatsResponse(
        total_users=stats['total_users'],
        active_users=stats['accessible_users'],  # Users in hierarchy
        pending_invitations=pending_invitations,
        managers_count=stats['total_farmers']  # Repurpose for now, can add later
    )


@router.get("/list", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List users accessible to current user (scoped by hierarchy)
    
    - Requires authentication
    - Returns users based on reporting structure:
      - Admin: All users in tenant
      - Field Manager: Self + invited field agents
      - Field Agent: Only self
    """
    from app.rbac import get_accessible_user_ids
    
    # Get accessible user IDs based on hierarchy
    accessible_ids = await get_accessible_user_ids(current_user['id'], db)
    
    # Get users along with their roles
    users_result = await db.execute(
        select(UserModel, Role)
        .join(Role, UserModel.role_id == Role.id)
        .where(UserModel.id.in_(accessible_ids))
        .order_by(UserModel.created_at.desc())
    )
    users = users_result.all() # .all() returns tuples of (UserModel, Role)
    
    return [
        UserResponse(
            id=u[0].id,
            name=u[0].name,
            email=u[0].email,
            role=u[1].name if u[1] else None, # Access role name from the Role object
            is_active=u[0].is_active,
            last_login=u[0].last_login,
            created_at=u[0].created_at
        )
        for u in users
    ]
