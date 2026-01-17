"""
Permission Checker Service

Checks if a user has permission to perform actions on resources.
"""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from modules.b2b.models import UserModel, Role, Resource, Action, RolePermission


async def has_permission(
    user_id: UUID,
    resource: str,
    action: str,
    db: AsyncSession,
    role_id: UUID | None = None,
    context_extras: dict | None = None
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
        role_id: Optional Role ID to skip User lookup if already known
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    current_role_id = role_id

    if not current_role_id:
        # Get user's role using explicit query (respects RLS)
        user_result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.role_id:
            return False
        current_role_id = user.role_id
    
    # Get role using explicit query (respects RLS)
    # Optimization: Could cache role existence/active check if often repeated
    role_result = await db.execute(
        select(Role).where(Role.id == current_role_id)
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


async def has_permission_with_plugins(
    user_id: UUID, 
    resource: str, 
    action: str, 
    db: AsyncSession,
    role_id: UUID | None = None,
    tenant_id: UUID | None = None
) -> bool:
    """
    Wrapper for has_permission that invokes the PluginRegistry.
    This is the primary entry point for plugin-aware permission checks.
    """
    from core.rbac.plugin_registry import plugin_registry
    from core.rbac.plugin_system import PermissionContext
    
    # 1. Fetch User Data (Minimal)
    # We need user dict for context.
    # Optimization: We might want to pass user object if available to avoid refetch.
    # For now, we fetch minimal user info.
    stmt = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return False

    user_dict = {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role_id": str(user.role_id) if user.role_id else None,
        # role name might be needed
    }
    
    # Enrich context
    # This might be expensive to do on every check. 
    # Ideally, enriched context is cached per request.
    enriched_user = await plugin_registry.enrich_user(user_dict, db)
    
    context = PermissionContext(
        user_id=str(user_id),
        user=enriched_user,
        resource_type=resource,
        resource_id=None, # Context extras can provide specific resource ID
        resource=None,    
        action=action,
        tenant_id=str(user.tenant_id)
        # extra_context passed if needed
    )
    
    # Define the core checker for the registry callback
    async def core_checker(ctx, session):
        # Maps registry context back to simple has_permission call
        return await has_permission(
            UUID(ctx.user_id), 
            ctx.resource_type, 
            ctx.action, 
            session,
            role_id=UUID(ctx.user['role_id']) if ctx.user.get('role_id') else None
        )
        
    return await plugin_registry.check_permission(context, core_checker, db)



async def get_user_permissions(user_id: UUID, db: AsyncSession) -> list[str]:
    """
    Get all permissions for a user as a list of 'resource:action' strings.
    Aggregates permissions from:
    1. Tenant Role (via role_permissions table)
    2. Team Roles (via team_role_definitions.permissions JSONB)
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        list: List of permission strings like ['shops:read', 'users:write']
    """
    permissions = set()

    # 1. Get Tenant Role Permissions
    result = await db.execute(
        select(Resource.name, Action.name)
        .select_from(UserModel)
        .join(Role, UserModel.role_id == Role.id)
        .join(RolePermission, Role.id == RolePermission.role_id)
        .join(Resource, RolePermission.resource_id == Resource.id)
        .join(Action, RolePermission.action_id == Action.id)
        .where(UserModel.id == user_id)
        .where(Role.is_active == True)
    )
    
    for resource_name, action_name in result:
        permissions.add(f"{resource_name}:{action_name}")

    # 2. Get Team Role Permissions
    # Join TeamMember -> TeamRoleDefinition to get the JSONB permissions list
    from modules.b2b.models.team_member import TeamMember
    from modules.b2b.models.team_role_definition import TeamRoleDefinition

    team_roles_result = await db.execute(
        select(TeamRoleDefinition.permissions)
        .join(TeamMember, TeamMember.team_role == TeamRoleDefinition.name)
        .where(TeamMember.user_id == user_id)
    )

    # Each row is a JSONB list of permissions: [{'resource': 'r', 'actions': ['read']}]
    # Note: The format in YAML/Seeder might be flattened or nested.
    # checking seed_rbac.py: flatten_permissions converts to [{'resource': 'r', 'action': 'a'}] ?
    # Let's handle the structure safely.
    
    for row in team_roles_result.scalars():
        if not row:
            continue
            
        for perm in row:
            # Handle flattened format from TeamRoleDefinition
            # Expected: {'resource': '...', 'actions': [...]} OR {'resource': '...', 'action': '...'}
            
            res = perm.get('resource')
            if not res:
                continue
                
            # Handle 'actions' list
            actions = perm.get('actions', [])
            if actions:
                for act in actions:
                    permissions.add(f"{res}:{act}")
            
            # Handle single 'action'
            action = perm.get('action')
            if action:
                permissions.add(f"{res}:{action}")
    
    return list(permissions)


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
