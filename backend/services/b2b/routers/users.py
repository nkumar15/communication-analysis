"""
User Management API Router

Handles user listing, statistics, and role management.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from services.b2b.schemas.users import UserResponse, UserStatsResponse, UserRoleUpdate
from services.b2b.services.user_service import user_service


router = APIRouter(prefix="/api/b2b/users", tags=["users"])


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user and invitation statistics for current tenant
    
    - Requires dashboard:read permission
    - Returns counts scoped to user's access level
    """
    stats = await user_service.get_user_stats(
        db=db,
        tenant_id=current_user['tenant_id'],
        user_id=current_user['id']
    )
    return UserStatsResponse(**stats)


@router.get("/list", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List users accessible to current user (scoped by hierarchy)
    
    - Requires authentication
    - Returns users based on reporting structure
    """
    users = await user_service.list_accessible_users(
        db=db,
        user_id=current_user['id']
    )
    return [UserResponse(**u) for u in users]


@router.put("/{user_id}/role", status_code=status.HTTP_200_OK)
async def update_user_role(
    user_id: UUID,
    role_update: UserRoleUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role in the tenant
    
    - Admin/Owner only
    - Cannot change own role
    - Enforces role hierarchy
    """
    result = await user_service.update_user_role(
        db=db,
        user_id=user_id,
        role_name=role_update.role,
        current_user_id=current_user['id'],
        current_user_role=current_user['role'],
        tenant_id=current_user['tenant_id']
    )
    await db.commit()
    return result
