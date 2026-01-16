#!/usr/bin/env python3
"""
RBAC Data Seeding Script

Seeds RBAC configuration from YAML files:
1. Core boilerplate (core/ directory) - Always loaded
2. Domain configuration (domain/ OR use_cases/) - Based on USE_CASE env var

Environment Variables:
- USE_CASE: Optional, loads a specific use case demo
  Examples: "bank_surveillance", "marketing_agency", "task_management"
  Default: Loads from domain/ directory

Usage:
  # Load core + domain configuration (default)
  python scripts/b2b/seed_rbac.py

  # Load core + bank surveillance demo
  USE_CASE=bank_surveillance python scripts/b2b/seed_rbac.py
  
  # Load core + marketing agency demo
  USE_CASE=marketing_agency python scripts/b2b/seed_rbac.py
  
  # Load core + task management demo
  USE_CASE=task_management python scripts/b2b/seed_rbac.py
"""

if __name__ == "__main__":
    # Fix sys.path BEFORE any imports to avoid platform.py collision
    import sys
    import os
    
    # Remove scripts directory from path to avoid shadowing stdlib
    sys.path = [p for p in sys.path if not p.endswith('/scripts/b2b') and not p.endswith('/scripts') and p != '']
    
    # Ensure /app is first in path for imports
    if '/app' not in sys.path:
        sys.path.insert(0, '/app')
    
    # Now safe to import everything else
    import asyncio
    import yaml
    from pathlib import Path
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm.attributes import flag_modified
    from core.db.session import database_url
    from modules.b2b.models.rbac import Resource, Action
    from modules.b2b.models.role_template import RoleTemplate
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    from modules.b2b.models.geographic_region import GeographicRegion
    from modules.b2b.models.scope_level import OrgTier
    from modules.b2b.models.tenant import TenantModel as Tenant
    from typing import Dict, Any

    # Directory paths
    SCRIPT_DIR = Path(__file__).parent
    CORE_DIR = SCRIPT_DIR / "core"
    DOMAIN_DIR = SCRIPT_DIR / "domain"
    USE_CASES_DIR = SCRIPT_DIR / "use_cases"
    
    # Determine which configuration to load
    use_case = os.getenv("USE_CASE", "")
    if use_case:
        CONFIG_DIR = USE_CASES_DIR / use_case
        if not CONFIG_DIR.exists():
            print(f"❌ Error: Use case '{use_case}' not found in {USE_CASES_DIR}")
            sys.exit(1)
        print(f"📦 Loading use case: {use_case}")
    else:
        CONFIG_DIR = DOMAIN_DIR
        print("📦 Loading domain configuration")

    def load_yaml(filepath: Path) -> dict:
        """Load and parse a YAML file"""
        if not filepath.exists():
            return {}
        
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}

    async def seed_org_tiers(db: AsyncSession, config: dict) -> None:
        """Seed org tiers from hierarchical_teams plugin config"""
        tiers_data = config.get('org_tiers', [])
        
        if not tiers_data:
            print("  ⚠️  No org tiers in hierarchical_teams config")
            return
        
        print(f"  📊 Seeding {len(tiers_data)} org tiers...")
        seeded_count = 0
        
        for tier_data in tiers_data:
            result = await db.execute(
                select(OrgTier).where(OrgTier.name == tier_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.display_name = tier_data['display_name']
                existing.description = tier_data.get('description')
                existing.hierarchy_order = tier_data.get('hierarchy_order', 0)
            else:
                org_tier = OrgTier(
                    name=tier_data['name'],
                    display_name=tier_data['display_name'],
                    description=tier_data.get('description'),
                    hierarchy_order=tier_data.get('hierarchy_order', 0)
                )
                db.add(org_tier)
                seeded_count += 1
        
        await db.flush()
        if seeded_count > 0:
            print(f"    ✓ Seeded {seeded_count} org tiers")
        else:
            print("    ✓ Org tiers already seeded")

    async def seed_actions(db: AsyncSession) -> None:
        """Seed RBAC actions from core/actions.yaml"""
        data = load_yaml(CORE_DIR / 'actions.yaml')
        actions_data = data.get('actions', [])
        
        if not actions_data:
            print("⚠️  No actions found")
            return
        
        # Check if already seeded
        result = await db.execute(select(Action).limit(1))
        if result.scalar_one_or_none():
            print("✓ Actions already seeded")
            return
        
        print(f"Seeding {len(actions_data)} actions...")
        actions = [
            Action(
                name=action['name'], 
                display_name=action['display_name'],
                description=action.get('description'),
                applicable_resources=action.get('applicable_resources')
            )
            for action in actions_data
        ]
        db.add_all(actions)
        await db.flush()
        print(f"✓ Seeded {len(actions)} actions")

    async def seed_domain_actions(db: AsyncSession) -> None:
        """Seed domain-specific actions from config/actions.yaml"""
        data = load_yaml(CONFIG_DIR / 'actions.yaml')
        actions_data = data.get('actions', [])
        
        if not actions_data:
            print("✓ No domain actions to seed")
            return
        
        print(f"Seeding {len(actions_data)} domain actions...")
        seeded_count = 0
        
        for action_data in actions_data:
            # Check if already seeded
            result = await db.execute(
                select(Action).where(Action.name == action_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                action = Action(
                    name=action_data['name'], 
                    display_name=action_data['display_name'],
                    description=action_data.get('description'),
                    applicable_resources=action_data.get('applicable_resources')
                )
                db.add(action)
                seeded_count += 1
        
        await db.flush()
        if seeded_count > 0:
            print(f"✓ Seeded {seeded_count} domain actions")
        else:
            print("✓ Domain actions already seeded")

    async def seed_saas_resources(db: AsyncSession) -> None:
        """Seed core SaaS resources from core/saas_resources.yaml"""
        data = load_yaml(CORE_DIR / 'saas_resources.yaml')
        resources_data = data.get('resources', [])
        
        if not resources_data:
            print("⚠️  No SaaS resources found")
            return
        
        print(f"Seeding {len(resources_data)} SaaS resources...")
        seeded_count = 0
        
        for res_data in resources_data:
            result = await db.execute(
                select(Resource).where(Resource.name == res_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                resource = Resource(
                    name=res_data['name'],
                    display_name=res_data['display_name'],
                    category=res_data.get('category'),
                    description=res_data.get('description'),
                    is_system_resource=res_data.get('is_system_resource', False)
                )
                db.add(resource)
                seeded_count += 1
        
        await db.flush()
        if seeded_count > 0:
            print(f"✓ Seeded {seeded_count} SaaS resources")
        else:
            print("✓ SaaS resources already seeded")

    async def seed_domain_resources(db: AsyncSession) -> None:
        """Seed domain resources from config directory"""
        # Try different possible keys in resources.yaml
        data = load_yaml(CONFIG_DIR / 'resources.yaml')
        resources_data = (
            data.get('resources', []) or
            data.get('bank_surveillance_resources', []) or
            data.get('marketing_agency_resources', []) or
            data.get('task_management_resources', [])
        )
        
        if not resources_data:
            print("✓ No domain resources to seed")
            return
        
        print(f"Seeding {len(resources_data)} domain resources...")
        seeded_count = 0
        
        for res_data in resources_data:
            result = await db.execute(
                select(Resource).where(Resource.name == res_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                resource = Resource(
                    name=res_data['name'],
                    display_name=res_data['display_name'],
                    category=res_data.get('category'),
                    description=res_data.get('description'),
                    is_system_resource=res_data.get('is_system_resource', False)
                )
                db.add(resource)
                seeded_count += 1
        
        await db.flush()
        if seeded_count > 0:
            print(f"✓ Seeded {seeded_count} domain resources")

    async def seed_saas_roles(db: AsyncSession) -> None:
        """Seed base tenant role templates from core/saas_roles.yaml"""
        data = load_yaml(CORE_DIR / 'saas_roles.yaml')
        templates_data = data.get('role_templates', [])
        
        if not templates_data:
            print("⚠️  No base role templates found")
            return
        
        print(f"Seeding {len(templates_data)} base role templates...")
        
        for template_data in templates_data:
            result = await db.execute(
                select(RoleTemplate).where(RoleTemplate.name == template_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.display_name = template_data['display_name']
                existing.description = template_data.get('description')
                existing.is_system_role = template_data.get('is_system_role', False)
                existing.is_default = template_data.get('is_default', False)
                existing.permissions = template_data.get('permissions', [])
                flag_modified(existing, 'permissions')
            else:
                template = RoleTemplate(
                    name=template_data['name'],
                    display_name=template_data['display_name'],
                    description=template_data.get('description'),
                    is_system_role=template_data.get('is_system_role', False),
                    is_default=template_data.get('is_default', False),
                    permissions=template_data.get('permissions', [])
                )
                db.add(template)
        
        await db.flush()
        print(f"✓ Processed {len(templates_data)} role templates")

    async def seed_additional_tenant_roles(db: AsyncSession) -> None:
        """Seed additional tenant roles from config/tenant_roles.yaml"""
        data = load_yaml(CONFIG_DIR / 'tenant_roles.yaml')
        roles_data = data.get('tenant_roles', [])
        
        if not roles_data:
            print("✓ No additional tenant roles to seed")
            return
        
        print(f"Seeding {len(roles_data)} additional tenant roles...")
        
        for role_data in roles_data:
            result = await db.execute(
                select(RoleTemplate).where(RoleTemplate.name == role_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.display_name = role_data['display_name']
                existing.description = role_data.get('description')
                existing.is_system_role = role_data.get('is_system_role', False)
                existing.is_default = role_data.get('is_default', False)
                existing.permissions = role_data.get('permissions', [])
                flag_modified(existing, 'permissions')
            else:
                role = RoleTemplate(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data.get('description'),
                    is_system_role=role_data.get('is_system_role', False),
                    is_default=role_data.get('is_default', False),
                    permissions=role_data.get('permissions', [])
                )
                db.add(role)
        
        await db.flush()
        print(f"✓ Processed {len(roles_data)} additional tenant roles")

    async def seed_base_team_roles(db: AsyncSession) -> None:
        """
        Seed base team roles from core/team_roles_base.yaml
        
        NOTE: Base team roles are SKIPPED if the use case defines custom team roles.
        This prevents role pollution where generic roles (team_manager, team_contributor)
        coexist with domain-specific roles (desk_surveillance_manager, account_manager).
        
        Logic:
        - If use case has custom team roles → Skip base roles (use domain roles only)
        - If use case has NO custom team roles → Load base roles (generic use case)
        """
        # Check if use case defines custom team roles
        use_case_team_roles_data = load_yaml(CONFIG_DIR / 'team_roles.yaml')
        use_case_team_roles = use_case_team_roles_data.get('team_roles', [])
        
        if use_case_team_roles:
            # Use case has custom team roles - skip base roles to avoid pollution
            print("✓ Skipping base team roles (use case defines custom team roles)")
            return
        
        # Use case has NO custom team roles - load base roles
        data = load_yaml(CORE_DIR / 'team_roles_base.yaml')
        roles_data = data.get('team_roles', [])
        
        if not roles_data:
            print("⚠️  No base team roles found")
            return
        
        print(f"Seeding {len(roles_data)} base team roles (generic use case)...")
        
        for role_data in roles_data:
            result = await db.execute(
                select(TeamRoleDefinition).where(
                    TeamRoleDefinition.name == role_data['name'],
                    TeamRoleDefinition.tenant_id.is_(None)
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.display_name = role_data['display_name']
                existing.description = role_data.get('description')
                existing.is_system = role_data.get('is_system', False)
                existing.is_default = role_data.get('is_default', False)
                existing.permissions = role_data.get('permissions', [])
                flag_modified(existing, 'permissions')
            else:
                role = TeamRoleDefinition(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data.get('description'),
                    is_system=role_data.get('is_system', False),
                    is_default=role_data.get('is_default', False),
                    tenant_id=None,
                    permissions=role_data.get('permissions', [])
                )
                db.add(role)
        
        await db.flush()
        print(f"✓ Processed {len(roles_data)} base team roles")

    async def seed_additional_team_roles(db: AsyncSession) -> None:
        """Seed additional team roles from config/team_roles.yaml"""
        data = load_yaml(CONFIG_DIR / 'team_roles.yaml')
        roles_data = data.get('team_roles', [])
        
        if not roles_data:
            print("✓ No additional team roles to seed")
            return
        
        print(f"Seeding {len(roles_data)} additional team roles...")
        
        for role_data in roles_data:
            result = await db.execute(
                select(TeamRoleDefinition).where(
                    TeamRoleDefinition.name == role_data['name'],
                    TeamRoleDefinition.tenant_id.is_(None)
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.display_name = role_data['display_name']
                existing.description = role_data.get('description')
                existing.is_system = role_data.get('is_system', False)
                existing.is_default = role_data.get('is_default', False)
                existing.permissions = role_data.get('permissions', [])
                existing.allowed_org_tiers = role_data.get('allowed_org_tiers', [])
                flag_modified(existing, 'permissions')
                flag_modified(existing, 'allowed_org_tiers')
            else:
                role = TeamRoleDefinition(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data.get('description'),
                    is_system=role_data.get('is_system', False),
                    is_default=role_data.get('is_default', False),
                    tenant_id=None,
                    permissions=role_data.get('permissions', []),
                    allowed_org_tiers=role_data.get('allowed_org_tiers', [])
                )
                db.add(role)
        
        await db.flush()
        print(f"✓ Processed {len(roles_data)} additional team roles")

    async def apply_tenant_permissions(db: AsyncSession) -> None:
        """Apply tenant permission overlays from config/tenant_permissions.yaml"""
        data = load_yaml(CONFIG_DIR / 'tenant_permissions.yaml')
        perms_by_role = data.get('tenant_permissions', {})
        
        if not perms_by_role:
            print("✓ No tenant permission overlays to apply")
            return
        
        print("Applying tenant permission overlays...")
        
        for role_name, perms in perms_by_role.items():
            result = await db.execute(
                select(RoleTemplate).where(RoleTemplate.name == role_name)
            )
            role = result.scalar_one_or_none()
            
            if not role:
                print(f"  ⚠️  Role '{role_name}' not found")
                continue
            
            # Add permissions
            current_perms = list(role.permissions)
            resources_to_update = {p.get('resource') for p in perms}
            
            # Remove old overlays for these resources
            filtered_perms = [p for p in current_perms if p.get('resource') not in resources_to_update]
            filtered_perms.extend(perms)
            
            if filtered_perms != current_perms:
                role.permissions = filtered_perms
                flag_modified(role, 'permissions')
        
        print("✓ Applied tenant permission overlays")

    async def apply_team_permissions(db: AsyncSession) -> None:
        """Apply team permission overlays from config/team_permissions.yaml"""
        data = load_yaml(CONFIG_DIR / 'team_permissions.yaml')
        perms_by_role = data.get('team_permissions', {})
        
        if not perms_by_role:
            print("✓ No team permission overlays to apply")
            return
        
        print("Applying team permission overlays...")
        
        for role_name, perms in perms_by_role.items():
            result = await db.execute(
                select(TeamRoleDefinition).where(
                    TeamRoleDefinition.name == role_name,
                    TeamRoleDefinition.tenant_id.is_(None)
                )
            )
            role = result.scalar_one_or_none()
            
            if not role:
                print(f"  ⚠️  Team role '{role_name}' not found")
                continue
            
            # Add permissions
            current_perms = list(role.permissions)
            resources_to_update = {p.get('resource') for p in perms}
            
            # Remove old overlays for these resources
            filtered_perms = [p for p in current_perms if p.get('resource') not in resources_to_update]
            filtered_perms.extend(perms)
            
            if filtered_perms != current_perms:
                role.permissions = filtered_perms
                flag_modified(role, 'permissions')
        
        print("✓ Applied team permission overlays")

    async def seed_geographic_regions(db: AsyncSession, config: Dict[str, Any]):
        """Seed geographic regions from plugins.yaml config"""
        regions_data = config.get('default_regions', [])
        
        if not regions_data:
            print("  ⚠️  No default_regions in plugins.yaml")
            return
        
        # Get tenant (assuming single tenant for demo)
        # In production, this would be per-tenant
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            print("  ⚠️  No tenant found for geographic region seeding")
            return
        
        print(f"\\n  📍 Seeding {len(regions_data)} geographic regions...")
        
        for region_data in regions_data:
            # Check if exists
            result = await db.execute(
                select(GeographicRegion).where(
                    GeographicRegion.tenant_id == tenant.id,
                    GeographicRegion.code == region_data['code']
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"    ✓ {region_data['code']} already exists")
                continue
            
            region = GeographicRegion(
                tenant_id=tenant.id,
                code=region_data['code'],
                name=region_data['name'],
                regulatory_jurisdiction=region_data.get('regulatory_jurisdiction')
            )
            db.add(region)
            print(f"    ✓ Created region: {region_data['code']} ({region_data['name']})")
        
        await db.flush()
        print(f"  ✓ Geographic regions seeded")

    async def initialize_plugins_if_enabled(db):
        """Load plugins only if RBAC_PLUGINS env var is set"""
        enabled = os.getenv('RBAC_PLUGINS', '').strip()
        if not enabled:
            print("✓ No RBAC plugins enabled")
            return
        
        # Manually load plugins.yaml from the CONFIG_DIR if valid
        # Given we are inside main(), CONFIG_DIR is available in scope? 
        # Yes, main() defines it but this function is outside. 
        # We need to pass it or re-derive. 
        
        # Let's assume this is called inside main() loop or we pass config path.
        # But CONFIG_DIR is global in the script scope? No, it's inside `if __name__`.
        # We should define these funcs inside main() or pass arguments.
        # The structure of this file is `if __name__ == "__main__": ... def functions ... async def main()`
        # So CONFIG_DIR is available in the closure of `main()` but not outside `main`.
        # Wait, `seed_actions` etc are defined inside `if __name__` but outside `async def main()`.
        # `CONFIG_DIR` is defined at top level of `if __name__`.
        # So `seed_geographic_regions` can access `CONFIG_DIR`.
        
        plugin_names = [p.strip() for p in enabled.split(',') if p.strip()]
        
        # Load plugin config
        config_file = CONFIG_DIR / 'plugins.yaml'
        # Check if file exists
        if config_file.exists():
            with open(config_file, 'r') as f:
                plugin_config = yaml.safe_load(f) or {}
        else:
            plugin_config = {}
        
        print(f"\\n🔌 Initializing {len(plugin_names)} RBAC plugins...")
        
        from core.rbac.plugin_registry import plugin_registry
        
        # We only really need to REGISTER for logic checks, but for seeding 
        # we strictly need to know which ones to run seeders for.
        # The registry is for runtime interceptors.
        
        # 0. PERSIST CONFIGURATION TO TENANT
        # This ensures AuthService picks it up at runtime (Per-Tenant Config)
        result = await db.execute(select(Tenant).limit(1))
        tenant = result.scalar_one_or_none()
        if tenant:
            print(f"  📝 updating tenant '{tenant.name}' plugins = {plugin_names}")
            tenant.plugins = plugin_names
            flag_modified(tenant, 'plugins')
            await db.flush()
        
        for name in plugin_names:
            if name == 'geographic_boundaries':
                # Register plugin for completeness
                # from backend.plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
                # plugin_registry.register(GeographicBoundariesPlugin())
                # Seed Data
                await seed_geographic_regions(db, plugin_config.get(name, {}))
            
            elif name == 'data_classification':
                # No seeding for now, only schema enums
                pass
            
            elif name == 'hierarchical_teams':
                # Seed org tiers from plugin config
                await seed_org_tiers(db, plugin_config.get(name, {}))
        
        print(f"✓ {len(plugin_names)} plugins processed")


    async def main():
        """Main seeding function"""
        print("\n" + "="*60)
        print("RBAC Data Seeding (From YAML)")
        print("="*60 + "\n")
        
        if not database_url:
            print("❌ Error: DATABASE_URL not configured")
            sys.exit(1)
        
        engine = create_async_engine(database_url, echo=False)
        
        try:
            async with AsyncSession(engine) as db:
                async with db.begin():
                    # Set admin context to bypass RLS for plugin tables
                    await db.execute(text("SET app.is_platform_admin = 'true'"))

                    # Step 1: Core SaaS boilerplate (always)
                    print("📦 Loading core boilerplate...")
                    await seed_actions(db)
                    await seed_saas_resources(db)
                    await seed_saas_roles(db)
                    await seed_base_team_roles(db)
                    print()
                    
                    # Step 2: Domain OR Use Case configuration
                    print(f"📦 Loading configuration from {CONFIG_DIR.name}/...")
                    await seed_domain_actions(db)
                    await seed_domain_resources(db)
                    # await seed_additional_tenant_roles(db)  # REMOVED: Tenant roles merged into team roles
                    await seed_additional_team_roles(db)
                    print()
                    
                    # Step 3: Apply permission overlays
                    print("📦 Applying permission overlays...")
                    await apply_tenant_permissions(db)
                    await apply_team_permissions(db)
                    await apply_team_permissions(db)
                    print()
                    
                    # Step 4: Plugin Initialization & Seeding
                    await initialize_plugins_if_enabled(db)
                    print()
                    
                    print("✓ All changes committed successfully")
            
            print("\n" + "="*60)
            print("✅ RBAC data seeding complete!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            await engine.dispose()

    asyncio.run(main())
