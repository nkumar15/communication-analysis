"""
B2B Authentication Middleware

This module provides authentication for B2B tenant users.
Extends the shared token validation with B2B-specific user lookup and RLS.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from core.middleware.auth import get_current_user
from core.database import get_db, current_tenant_id
from services.b2b.models import UserModel, Role


async def get_current_active_user(
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current B2B user from database using Firebase ID token
    
    Also sets the tenant context for Row Level Security enforcement.
    
    Returns dict with user fields including 'id', 'role', etc.
    """
    firebase_uid = decoded_token.get('uid')
    if not firebase_uid:
         raise HTTPException(status_code=401, detail="Invalid token")
         
    result = await db.execute(select(UserModel).where(UserModel.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Set tenant context for Row Level Security
    # This ensures all subsequent queries are automatically scoped to this tenant
    current_tenant_id.set(str(user.tenant_id))
        
    # Fetch role slug and display name
    role_slug = None
    role_display_name = None
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role_obj = role_result.scalar_one_or_none()
        if role_obj:
            role_slug = role_obj.name
            role_display_name = role_obj.display_name

    return {
        "id": user.id,
        "email": user.email,
        "firebase_uid": user.firebase_uid,
        "tenant_id": user.tenant_id,
        "role_id": user.role_id,
        "role": role_slug,
        "role_display_name": role_display_name
    }


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to enforce role-based access control.
    
    Args:
        allowed_roles: List of role slugs allowed to access the endpoint.
        
    Returns:
        Dependency function that checks the user's role.
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_active_user)):
        if not current_user.get("role"):
            raise HTTPException(status_code=403, detail="User has no role assigned")
            
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Operation not permitted. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
        
    return role_checker
