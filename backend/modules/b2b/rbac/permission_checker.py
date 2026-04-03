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
    Check if user has permission for resource:action (Layer 1: Tenant-level RBAC)
    
    Args:
        user_id: User ID to check
        resource: Resource name
        action: Action name
        db: Database session
        role_id: Optional Tenant Role ID to skip User lookup
        
    Returns:
        bool: True if authorized at the tenant level
    """
    current_role_id = role_id
    if not current_role_id:
        user_result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            current_role_id = user.role_id

    if current_role_id:
        tenant_perm_stmt = (
            select(RolePermission)
            .join(Resource, RolePermission.resource_id == Resource.id)
            .join(Action, RolePermission.action_id == Action.id)
            .where(RolePermission.role_id == current_role_id)
            .where(Resource.name == resource)
            .where(Action.name == action)
        )
        tenant_perm_result = await db.execute(tenant_perm_stmt)
        perm = tenant_perm_result.scalar_one_or_none()
        if perm:
            return True

    return False


async def has_permission_with_plugins(
    user_id: UUID, 
    resource: str, 
    action: str, 
    db: AsyncSession,
    role_id: UUID | None = None,
    tenant_id: UUID | None = None,
    extra_context: dict | None = None
) -> bool:
    """
    The primary entry point for 3-layer RBAC checks.
    
    Flow:
    1. Interceptor (Plugin Before)
    2. Core (Tenant + Team/Business RBAC)
    3. Filter (Plugin After - Geo/Clearance)
    
    Enforcement depends on tenant subscription-enabled plugins.
    """
    from core.rbac.plugin_registry import plugin_registry
    from core.rbac.plugin_system import PermissionContext
    from modules.b2b.models import TenantModel
    from modules.b2b.models.team_member import TeamMember
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    
    # 1. OPTIMIZATION: Check if user context is already enriched (e.g., by Middleware)
    # Use the explicit context_enriched flag set by plugin_registry.enrich_user().
    # Do NOT rely on geographic_scopes presence — it exists in the base context even
    # when enrichment failed, which would cause a half-baked context to be trusted.
    enriched_user = None
    enabled_plugins = []

    user_from_context = extra_context.get("user") if extra_context else None
    if user_from_context and user_from_context.get("context_enriched") is True:
        enriched_user = user_from_context
        enabled_plugins = enriched_user.get("enabled_plugins", [])
    
    # 2. Fallback: Fetch and Enrich if not provided (e.g. background tasks)
    if not enriched_user:
        # Fetch User and Tenant Context
        user_stmt = select(UserModel).where(UserModel.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False
    
        tenant_stmt = select(TenantModel).where(TenantModel.id == user.tenant_id)
        tenant_result = await db.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            return False
    
        # Extract enabled plugins from subscription-driven tenant.features
        enabled_plugins = tenant.features.get('plugins', []) if tenant.features else []
    
        # Get Tenant Role Name
        role_name = None
        if user.role_id:
            role_stmt = select(Role.name).where(Role.id == user.role_id)
            role_name_result = await db.execute(role_stmt)
            role_name = role_name_result.scalar()
    
        # Get all Team Roles
        team_roles_stmt = (
            select(TeamRoleDefinition.name)
            .join(TeamMember, TeamMember.team_role_id == TeamRoleDefinition.id)
            .where(TeamMember.user_id == user_id)
        )
        team_roles_result = await db.execute(team_roles_stmt)
        team_role_names = [name for name in team_roles_result.scalars()]
    
        user_dict = {
            "id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role_id": str(user.role_id) if user.role_id else None,
            "role": role_name,
            "team_roles": team_role_names,
            "enabled_plugins": enabled_plugins
        }
        
        # Enrich User Context with Plugins
        enriched_user = await plugin_registry.enrich_user(user_dict, db, enabled_plugin_names=enabled_plugins)
    
    # 3. Create Permission Context
    context = PermissionContext(
        user_id=str(user_id),
        user=enriched_user,
        resource_type=resource,
        resource_id=extra_context.get("resource_id") if extra_context else None,
        resource=extra_context.get("resource") if extra_context else None,
        action=action,
        tenant_id=str(enriched_user['tenant_id']),
        extra_context=extra_context
    )
    
    # 3. Define the core checker (Layer 2: Business/Team Role)
    async def core_checker(ctx, session):
        # 3.1 Check Layer 1 (Tenant Role)
        tenant_authorized = await has_permission(
            UUID(ctx.user_id), 
            ctx.resource_type, 
            ctx.action, 
            session,
            role_id=UUID(ctx.user['role_id']) if ctx.user.get('role_id') else None
        )
        if tenant_authorized:
            return True
            
        # 3.2 Check Layer 2 (Team/Business Role)
        team_perm_stmt = (
            select(TeamRoleDefinition.permissions)
            .join(TeamMember, TeamMember.team_role_id == TeamRoleDefinition.id)
            .where(TeamMember.user_id == UUID(ctx.user_id))
        )
        team_perm_results = await session.execute(team_perm_stmt)
        
        for permissions_json in team_perm_results.scalars():
            if not permissions_json:
                continue
            for perm in permissions_json:
                if perm.get('resource') == ctx.resource_type:
                    actions = perm.get('actions', [])
                    if ctx.action in actions or perm.get('action') == ctx.action:
                        return True
        return False
        
    return await plugin_registry.check_permission(context, core_checker, db, enabled_plugin_names=enabled_plugins)



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
        .join(TeamMember, TeamMember.team_role_id == TeamRoleDefinition.id)
        .where(TeamMember.user_id == user_id)
    )

    # Each row is a JSONB list of permissions: [{'resource': 'r', 'actions': ['read']}]
    # Note: The format in YAML/Seeder might be flattened or nested.
    # checking seed_rbac.py: flatten_permissions converts to [{'resource': 'r', 'action': 'a'}] ?
    # Let's handle the structure safely.
    
    # Each row is a JSONB list of permissions
    for row in team_roles_result.scalars():
        if not row:
            continue
            
        for perm in row:
            # Handle flattened format from TeamRoleDefinition
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
