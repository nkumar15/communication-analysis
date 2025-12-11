"""
Permission Checker Service

Checks if a user has permission to perform actions on resources.
"""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.b2b.models import UserModel, Role, Resource, Action, RolePermission


async def has_permission(
    user_id: UUID,
    resource: str,
    action: str,
    db: AsyncSession
) -> bool:
    """
    Check if user has permission for resource:action
    
    This function checks the role_permissions table, NOT role names.
    This design allows role names to change while permissions remain stable.
    
    Args:
        user_id: User ID to check
        resource: Resource name (e.g., 'projects', 'users')
        action: Action name (e.g., 'read', 'write')
        db: Database session
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    # Get user's role using explicit query (respects RLS)
    user_result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user or not user.role_id:
        return False
    
    # Get role using explicit query (respects RLS)
    role_result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = role_result.scalar_one_or_none()
    
    if not role or not role.is_active:
        return False
    
    # Check role_permissions table for explicit permission grant
    result = await db.execute(
        select(RolePermission)
        .join(Resource, RolePermission.resource_id == Resource.id)
        .join(Action, RolePermission.action_id == Action.id)
        .where(RolePermission.role_id == role.id)
        .where(Resource.name == resource)
        .where(Action.name == action)
    )
    
    permission = result.scalar_one_or_none()
    return permission is not None


async def get_user_permissions(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get all permissions for a user as a list of 'resource:action' strings
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        list: List of permission strings like ['shops:read', 'users:write']
    """
    # Get user using explicit query (respects RLS)
    user_result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user or not user.role_id:
        return []
    
    # Get role using explicit query (respects RLS)
    role_result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = role_result.scalar_one_or_none()
    
    if not role or not role.is_active:
        return []
    
    # Get all permissions for this role
    result = await db.execute(
        select(Resource.name, Action.name)
        .select_from(RolePermission)
        .join(Resource, RolePermission.resource_id == Resource.id)
        .join(Action, RolePermission.action_id == Action.id)
        .where(RolePermission.role_id == role.id)
    )
    
    permissions = []
    for resource_name, action_name in result:
        permissions.append(f"{resource_name}:{action_name}")
    
    return permissions


async def get_user_role_name(user_id: UUID, db: AsyncSession) -> str | None:
    """
    Get the role name for a user
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        str | None: Role name ('admin', 'field_manager', 'field_agent') or None
    """
    # Get user using explicit query (respects RLS)
    user_result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user or not user.role_id:
        return None
    
    # Get role using explicit query (respects RLS)
    role_result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = role_result.scalar_one_or_none()
    
    return role.name if role else None
