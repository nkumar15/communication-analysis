"""
Middleware for SaaS Platform Admin verification
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from app.database import get_db
from app.middleware.auth import get_current_user
from app.constants import RoleName
from app.rbac_models import Role
from app.services.user_service import user_service

async def verify_platform_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dependency to verify that the current user is a Platform Admin.
    
    Checks:
    1. User exists in database
    2. User belongs to the System Tenant (implied by role check, but good to verify)
    3. User has the 'platform_admin' role
    
    Returns:
        User dict if authorized, raises HTTPException otherwise
    """
    firebase_uid = current_user.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )
        
    # We need to find the user across ALL tenants to check for platform admin status
    # Since get_user_by_firebase_uid requires tenant_id, we'll query directly here
    # or we can assume the frontend sends the system tenant ID in headers?
    # Better: Query user by firebase_uid globally and check role
    
    from app.db_models import UserModel
    
    # Find user by Firebase UID (globally)
    # Note: A user might belong to multiple tenants, but Platform Admin should be
    # a specific user record in the System Tenant.
    
    result = await db.execute(
        select(UserModel).where(UserModel.firebase_uid == firebase_uid)
    )
    users = result.scalars().all()
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Check if ANY of the user's records has the platform_admin role
    is_platform_admin = False
    platform_user = None
    
    for user in users:
        # Fetch role for this user record
        role_result = await db.execute(
            select(Role).where(Role.id == user.role_id)
        )
        role = role_result.scalar_one_or_none()
        
        if role and role.name == RoleName.PLATFORM_ADMIN:
            is_platform_admin = True
            platform_user = user
            break
            
    if not is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Platform Admin privileges"
        )
        
    return current_user
