import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from modules.b2b.models.rbac import Resource, Action
from modules.b2b.models.role_template import RoleTemplate
from modules.b2b.models.team_role_definition import TeamRoleDefinition
from modules.b2b.models.plugin_template import PluginTemplate

async def set_platform_context(db: AsyncSession):
    """Set the database context to platform admin to bypass RLS for global seeding."""
    await db.execute(text("SELECT set_config('app.current_user_role', 'platform_admin', false)"))
    await db.execute(text("SELECT set_config('app.is_platform_admin', 'true', false)"))

def load_yaml(filepath: Path) -> dict:
    """Load and parse a YAML file"""
    if not filepath.exists():
        return {}
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}

def flatten_permissions(permissions: list) -> list:
    """Flatten permissions from YAML format to resource+action pairs."""
    flattened = []
    for p in permissions:
        resource = p.get('resource')
        actions = p.get('actions', [])
        action = p.get('action')
        
        if action:
            flattened.append({'resource': resource, 'action': action})
        if actions:
            for a in actions:
                flattened.append({'resource': resource, 'action': a})
        if not action and not actions:
            flattened.append(p)
    return flattened

async def seed_actions(db: AsyncSession, config_dir: Path, only_system: bool = False) -> None:
    filepath = config_dir / 'foundation_actions.yaml'
    if not filepath.exists():
        filepath = config_dir / 'overlay_actions.yaml'
        
    data = load_yaml(filepath)
    actions_data = data.get('actions', [])
    if not actions_data: return

    for action_data in actions_data:
        result = await db.execute(select(Action).where(Action.name == action_data['name']))
        existing = result.scalar_one_or_none()
        if not existing:
            action = Action(
                name=action_data['name'], 
                display_name=action_data['display_name'],
                description=action_data.get('description'),
                applicable_resources=action_data.get('applicable_resources')
            )
            db.add(action)
    await db.flush()

async def seed_resources(db: AsyncSession, config_dir: Path, is_system: bool = False, only_system: bool = False) -> None:
    filepath = config_dir / 'foundation_resources.yaml'
    if not filepath.exists():
        filepath = config_dir / 'overlay_resources.yaml'
    
    data = load_yaml(filepath)
    # Support different keys for domain-specific resources
    resources_data = (
        data.get('resources', []) or 
        data.get('bank_surveillance_resources', []) or 
        data.get('marketing_agency_resources', []) or 
        data.get('task_management_resources', [])
    )
    if not resources_data: return

    for res_data in resources_data:
        # SMART FILTER: If only_system is requested, skip non-system resources
        # This prevents domain-specific clutter (like projects/rag_enron) in other use cases
        if only_system and res_data.get('is_system_resource', is_system) is False:
            continue
            
        result = await db.execute(select(Resource).where(Resource.name == res_data['name']))
        existing = result.scalar_one_or_none()
        if not existing:
            resource = Resource(
                name=res_data['name'],
                display_name=res_data['display_name'],
                category=res_data.get('category'),
                description=res_data.get('description'),
                is_system_resource=res_data.get('is_system_resource', is_system)
            )
            db.add(resource)
    await db.flush()

async def seed_role_templates(db: AsyncSession, config_dir: Path) -> None:
    # Use foundation_saas_roles.yaml for foundation, fallback to overlay
    filepath = config_dir / 'foundation_saas_roles.yaml'
    if not filepath.exists():
        filepath = config_dir / 'overlay_saas_roles.yaml'
    if not filepath.exists():
        filepath = config_dir / 'roles.yaml'
    
    data = load_yaml(filepath)
    templates_data = data.get('role_templates', []) or data.get('tenant_roles', [])
    if not templates_data: return

    for template_data in templates_data:
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == template_data['name']))
        existing = result.scalar_one_or_none()
        
        perms = template_data.get('permissions', [])
        if existing:
            existing.display_name = template_data['display_name']
            existing.description = template_data.get('description')
            existing.is_system_role = template_data.get('is_system_role', False)
            existing.permissions = perms
            flag_modified(existing, 'permissions')
        else:
            template = RoleTemplate(
                name=template_data['name'],
                display_name=template_data['display_name'],
                description=template_data.get('description'),
                is_system_role=template_data.get('is_system_role', False),
                is_default=template_data.get('is_default', False),
                permissions=perms
            )
            db.add(template)
    await db.flush()

async def seed_team_roles(db: AsyncSession, config_dir: Path) -> None:
    filepath = config_dir / 'foundation_team_roles.yaml'
    if not filepath.exists():
        filepath = config_dir / 'overlay_team_roles.yaml'
        
    data = load_yaml(filepath)
    roles_data = data.get('team_roles', [])
    if not roles_data: return

    for role_data in roles_data:
        result = await db.execute(select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == role_data['name'],
            TeamRoleDefinition.tenant_id.is_(None)
        ))
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.display_name = role_data['display_name']
            existing.description = role_data.get('description')
            existing.permissions = role_data.get('permissions', [])
            existing.allowed_org_tiers = role_data.get('allowed_org_tiers', [])
            flag_modified(existing, 'permissions')
            flag_modified(existing, 'allowed_org_tiers')
        else:
            role = TeamRoleDefinition(
                name=role_data['name'],
                display_name=role_data['display_name'],
                description=role_data.get('description'),
                tenant_id=None,
                permissions=role_data.get('permissions', []),
                allowed_org_tiers=role_data.get('allowed_org_tiers', [])
            )
            db.add(role)
    await db.flush()

async def apply_permission_overlays(db: AsyncSession, config_dir: Path) -> None:
    # Tenant Overlays
    tenant_data = load_yaml(config_dir / 'tenant_permissions.yaml')
    tenant_perms = tenant_data.get('tenant_permissions', {})
    for role_name, perms in tenant_perms.items():
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == role_name))
        role = result.scalar_one_or_none()
        if role:
            role.permissions = flatten_permissions(list(role.permissions) + perms)
            flag_modified(role, 'permissions')

    # Team Overlays
    team_data = load_yaml(config_dir / 'team_permissions.yaml')
    team_perms = team_data.get('team_permissions', {})
    for role_name, perms in team_perms.items():
        result = await db.execute(select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == role_name,
            TeamRoleDefinition.tenant_id.is_(None)
        ))
        role = result.scalar_one_or_none()
        if role:
            role.permissions = flatten_permissions(list(role.permissions) + perms)
            flag_modified(role, 'permissions')
    await db.flush()

async def seed_plugin_templates(db: AsyncSession, config_dir: Path, filename: str = 'foundation_plugins.yaml') -> None:
    """Seed global plugin templates into the master catalog."""
    filepath = config_dir / filename
    if not filepath.exists():
        filepath = config_dir / 'overlay_plugins.yaml'
    if not filepath.exists():
        return
        
    data = load_yaml(filepath)
    if not data:
        return

    # Categories to extract
    categories = ['geographic_boundaries', 'data_classification', 'hierarchical_teams']
    
    for category in categories:
        if category in data:
            result = await db.execute(select(PluginTemplate).where(PluginTemplate.plugin_slug == category))
            existing = result.scalar_one_or_none()
            
            if existing:
                # Deep merge: overlay data merges with existing foundation data
                merged_data = deep_merge_plugin_data(existing.template_data, data[category])
                existing.template_data = merged_data
                flag_modified(existing, 'template_data')
            else:
                template = PluginTemplate(
                    plugin_slug=category,
                    template_data=data[category]
                )
                db.add(template)
    
    await db.flush()

def deep_merge_plugin_data(base: dict, overlay: dict) -> dict:
    """
    Deep merge overlay plugin data into base.
    - Dicts: Recursive merge
    - Lists: Overlay replaces (for seed_data)
    - Scalars: Overlay wins
    """
    import copy
    result = copy.deepcopy(base)
    
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_plugin_data(result[key], value)
        else:
            # For lists and scalars, overlay wins (e.g., seed_data should replace)
            result[key] = value
            
    return result

