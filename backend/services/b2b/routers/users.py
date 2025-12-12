from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.middleware import get_current_active_user
from services.b2b.models import InvitationModel
from services.b2b.rbac import get_accessible_user_ids
from services.b2b.models import UserModel
from services.b2b.models import Role


# Placeholder block removed - moved logic into list_users endpoint
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/b2b/users", tags=["users"])


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
    """
    from services.b2b.rbac import get_dashboard_stats, require_permission
    
    # Check if user has dashboard access (admin and field_manager only)
    # This will raise 403 if user doesn't have permission
    from services.b2b.rbac.permission_checker import has_permission
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
        managers_count=stats.get('total_projects', 0)  # Default to 0 if key doesn't exist
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
      - Admin: All users in tenan
    """
    from services.b2b.rbac import get_accessible_user_ids
    
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

class UserRoleUpdate(BaseModel):
    role: str

@router.put("/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role in the tenant
    
    - Admin/Owner only
    - Cannot change own role if owner
    """
    from services.b2b.rbac.permission_checker import has_permission
    
    # 1. Check permission (admin or owner of tenant)
    # We use 'users:write' permission for this, which Admin/Owner should have
    if not await has_permission(current_user['id'], 'users', 'invite', db) and current_user['role'] != 'owner':
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Only admins can update roles."
        )

    # 2. Get target user
    # 2. Get target user with Role
    result = await db.execute(
        select(UserModel, Role.name.label("role_name"))
        .join(Role, UserModel.role_id == Role.id)
        .where(
            UserModel.id == user_id,
            UserModel.tenant_id == current_user['tenant_id']
        )
    )
    user_row = result.first()
    
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = user_row[0]
    user_role_name = user_row.role_name
        
    # 3. Validate Role
    # Check if role exists in tenant roles
    role_result = await db.execute(
        select(Role).where(
            Role.tenant_id == current_user['tenant_id'],
            Role.name == role_update.role
        )
    )
    role_obj = role_result.scalar_one_or_none()
    
    if not role_obj:
        # Fallback: Check if it's a template role that hasn't been instantiated yet?
        # For simplify/correctness in this codebase, custom roles and admin roles should exist in Roles table
        # If not found, it's an invalid role for this tenant
        raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"Role '{role_update.role}' not found."
        )

    # 4. Strict Hierarchy Checks (Prevent Privilege Escalation/Lockout)
    
    # 4.1 Prevent Self-Modification (Prevent Lockout)
    if user.id == current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role. Ask another admin to do it."
        )

    # 4.2 Admin vs Owner Protection
    # If target is Owner, only Owner can modify
    if user_role_name == 'owner' and current_user['role'] != 'owner':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot modify the Owner's role."
        )

    # 4.3 Admin vs Admin Protection
    # If target is Admin, only Owner can modify
    if user_role_name == 'admin' and current_user['role'] != 'owner':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot modify other Admins. Only the Owner can do that."
        )

    # 4.4 Prevent elevating to Owner
    if role_update.role == 'owner':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign 'owner' role via this endpoint. Use specific transfer ownership process."
        )
        
    # 5. Update
    # FIXED: Assign role_id, not role name string
    user.role_id = role_obj.id
    print(f"User {user.id} role updated to {role_update.role} ({role_obj.id})")
    await db.commit()
    
    return {"message": "User role updated successfully"}
