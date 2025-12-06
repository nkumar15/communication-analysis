"""
B2B Authentication Middleware

This module provides authentication for B2B tenant users.
Extends the shared token validation with B2B-specific user lookup and RLS.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
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
    
    # Extract tenant ID from token
    # Use helper or direct access (helper is cleaner but adds import)
    # Direct access to match valid structure:
    firebase_tenant_id = decoded_token.get('firebase', {}).get('tenant')
    if not firebase_tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing tenant ID")

    # 1. Resolve Tenant UUID (No RLS on tenants table)
    # We verify the tenant exists and get its UUID to set the RLS context
    from services.b2b.services.tenant_service import tenant_service
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found")
    
    # SECURITY: Verify tenant is activated
    # Pending tenants should not be able to access B2B endpoints
    if tenant.activation_status != 'active':
        raise HTTPException(
            status_code=403, 
            detail="Tenant is not yet activated. Please complete the activation process."
        )

    # 2. Set RLS Context
    # Now valid queries to private tables (users, teams) will work
    current_tenant_id.set(str(tenant.id))
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant.id}'"))

    # 3. Lookup User (RLS Enabled)
    # This query matches the policy: tenant_id = app.current_tenant_id
    result = await db.execute(
        select(UserModel).where(UserModel.firebase_uid == firebase_uid)
    )
    user_row = result.scalar_one_or_none()
    
    if not user_row:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check if user is active
    if not user_row.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
        
    # Fetch role slug and display name (now with RLS context set)
    role_slug = None
    role_display_name = None
    if user_row.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user_row.role_id))
        role_obj = role_result.scalar_one_or_none()
        if role_obj:
            role_slug = role_obj.name
            role_display_name = role_obj.display_name

    return {
        "id": user_row.id,
        "email": user_row.email,
        "firebase_uid": user_row.firebase_uid,
        "tenant_id": user_row.tenant_id,
        "role_id": user_row.role_id,
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
