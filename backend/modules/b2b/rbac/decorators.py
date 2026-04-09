"""
Permission Decorators for FastAPI Endpoints

Use these to protect endpoints with permission checks.
"""
from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from modules.b2b.middleware import get_current_active_user
from core.db.session import get_db
from .permission_checker import has_permission, get_user_role_name


def require_permission(resource: str, action: str):
    """
    Decorator to require permission for an endpoint
    
    Usage:
        @router.get("/shops")
        @require_permission('shops', 'read')
        async def list_shops(current_user: dict = Depends(get_current_user)):
            ...
    
    Args:
        resource: Resource name (e.g., 'shops', 'users')
        action: Action name (e.g., 'read', 'write')
    """
    async def permission_dependency(
        current_user: dict = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Check if user has required permission (3-layer aware)"""
        from .permission_checker import has_permission_with_plugins
        
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Check permission using the comprehensive 3-layer flow
        allowed = await has_permission_with_plugins(
            user_id, 
            resource, 
            action, 
            db, 
            role_id=current_user.get('role_id'),
            extra_context={"user": current_user}
        )
        
        if not allowed:
            from infrastructure.monitoring import increment_rbac_denial
            increment_rbac_denial(resource, action)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}"
            )
        
        return current_user
    
    return Depends(permission_dependency)


def require_role(*allowed_roles: str):
    """
    Decorator to require specific role(s) for an endpoint
    
    Usage:
        @router.post("/invite")
        @require_role('admin', 'owner')
        async def invite_user(current_user: dict = Depends(get_current_user)):
            ...
    
    Args:
        *allowed_roles: Role names that are allowed (e.g., 'admin', 'owner')
    """
    async def role_dependency(
        current_user: dict = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Check if user has required role"""
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Use cached role slug from token/middleware if available
        role_slug = current_user.get('role')
        
        # Determine role name (fallback to DB if missing in token context)
        if not role_slug:
            role_slug = await get_user_role_name(user_id, db)
            
        if role_slug not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return current_user
    
    return Depends(role_dependency)
