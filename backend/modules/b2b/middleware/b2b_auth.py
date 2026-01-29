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
from core.db.session import get_db, current_tenant_id
from modules.b2b.models import UserModel, Role


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
    from modules.b2b.services.tenant_service import tenant_service
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Tenant not found")
    
    # SECURITY: Verify tenant is activated and not deactivated by admin
    # Pending tenants should not be able to access B2B endpoints
    if tenant.activation_status != 'active':
        raise HTTPException(
            status_code=403, 
            detail="Tenant is not yet activated. Please complete the activation process."
        )
    
    # Check if tenant was deactivated by platform admin
    if not tenant.is_active:
        raise HTTPException(
            status_code=403,
            detail="This organization has been deactivated. Please contact your administrator."
        )

    # 2. Set RLS Context
    # Now valid queries to private tables (users, teams) will work
    current_tenant_id.set(str(tenant.id))
    from core.db.rls import rls_service
    await rls_service.set_tenant_context(db, tenant.id)

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

    # Create base user context
    # converting UUIDs to strings to match Permission Checker expectations
    user_context = {
        "id": str(user_row.id),
        "email": user_row.email,
        "firebase_uid": user_row.firebase_uid,
        "tenant_id": str(user_row.tenant_id),
        "role_id": str(user_row.role_id) if user_row.role_id else None,
        "role": role_slug,
        "role_display_name": role_display_name,
        "geographic_scopes": [str(g) for g in (user_row.geographic_scopes or [])],
        "enabled_plugins": tenant.features.get('plugins', []) if tenant.features else []
    }

    # 4. Enrich User Context via Plugins (Fix for Geographic Scope Leak)
    # This ensures team-based scopes provided by GeographicBoundariesPlugin are merged
    # into the user context before any route handler or permission check runs.
    try:
        from core.rbac.plugin_registry import plugin_registry
        enabled_plugins = user_context["enabled_plugins"]
        
        # Enrich the user dict (e.g., adds geographic_scopes from team membership)
        enriched_user = await plugin_registry.enrich_user(
            user_context, 
            db, 
            enabled_plugin_names=enabled_plugins
        )
        return enriched_user
        
    except Exception as e:
        # Fallback to base context if enrichment fails, but log error
        import logging
        logging.getLogger(__name__).error(f"Plugin enrichment failed for user {user_row.id}: {e}")
        return user_context



