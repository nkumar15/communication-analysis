#!/usr/bin/env python3
"""
RBAC and Domain Data Seeding Script

Seeds all RBAC data (actions, resources, role templates, team roles) from YAML files.
Run this after migrations to populate the database with initial configuration.

YAML Files Used:
- actions.yaml: Universal RBAC actions
- resources.yaml: SaaS boilerplate resources
- domain_resources.yaml: Domain-specific resources
- role_templates.yaml: Default role templates
- team_role_definitions.yaml: Default team roles
- domain_role_permissions.yaml: Domain permissions for role templates
- domain_team_permissions.yaml: Domain permissions for team roles
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
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm.attributes import flag_modified
    from core.database import database_url
    from services.b2b.models.rbac import Resource, Action
    from services.b2b.models.role_template import RoleTemplate
    from services.b2b.models.team_role_definition import TeamRoleDefinition

    # Base path for YAML files
    YAML_DIR = Path(__file__).parent

    def load_yaml(filename: str) -> dict:
        """Load and parse a YAML file"""
        filepath = YAML_DIR / filename
        if not filepath.exists():
            print(f"⚠️  Warning: {filename} not found")
            return {}
        
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}

    async def seed_actions(db: AsyncSession) -> None:
        """Seed RBAC actions from actions.yaml"""
        data = load_yaml('actions.yaml')
        actions_data = data.get('actions', [])
        
        if not actions_data:
            print("⚠️  No actions found in actions.yaml")
            return
        
        # Check if already seeded
        result = await db.execute(select(Action).limit(1))
        if result.scalar_one_or_none():
            print("✓ Actions already seeded")
            return
        
        print(f"Seeding {len(actions_data)} actions...")
        actions = [
            Action(name=action['name'], display_name=action['display_name'])
            for action in actions_data
        ]
        db.add_all(actions)
        await db.flush()
        print(f"✓ Seeded {len(actions)} actions")

    async def seed_resources(db: AsyncSession) -> None:
        """Seed SaaS boilerplate resources from resources.yaml"""
        data = load_yaml('resources.yaml')
        resources_data = data.get('resources', [])
        
        if not resources_data:
            print("⚠️  No resources found in resources.yaml")
            return
        
        # Check if already seeded (check for a common resource)
        result = await db.execute(select(Resource).where(Resource.name == 'dashboard'))
        if result.scalar_one_or_none():
            print("✓ SaaS resources already seeded")
            return
        
        print(f"Seeding {len(resources_data)} SaaS resources...")
        resources = [
            Resource(
                name=res['name'],
                display_name=res['display_name'],
                category=res.get('category'),
                description=res.get('description')
            )
            for res in resources_data
        ]
        db.add_all(resources)
        await db.flush()
        print(f"✓ Seeded {len(resources)} SaaS resources")

    async def seed_domain_resources(db: AsyncSession) -> None:
        """Seed domain-specific resources from domain_resources.yaml"""
        data = load_yaml('domain_resources.yaml')
        resources_data = data.get('resources', [])
        
        if not resources_data:
            print("⚠️  No domain resources found in domain_resources.yaml")
            return
        
        # Check if already seeded
        result = await db.execute(select(Resource).where(Resource.name == 'projects'))
        if result.scalar_one_or_none():
            print("✓ Domain resources already seeded")
            return
        
        print(f"Seeding {len(resources_data)} domain resources...")
        resources = [
            Resource(
                name=res['name'],
                display_name=res['display_name'],
                category=res.get('category'),
                description=res.get('description')
            )
            for res in resources_data
        ]
        db.add_all(resources)
        await db.flush()
        print(f"✓ Seeded {len(resources)} domain resources")

    async def seed_role_templates(db: AsyncSession) -> None:
        """Seed role templates from role_templates.yaml"""
        data = load_yaml('role_templates.yaml')
        templates_data = data.get('role_templates', [])
        
        if not templates_data:
            print("⚠️  No role templates found in role_templates.yaml")
            return
        
        print(f"Seeding {len(templates_data)} role templates...")
        
        for template_data in templates_data:
            # Check if already exists
            result = await db.execute(
                select(RoleTemplate).where(RoleTemplate.name == template_data['name'])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing template
                existing.display_name = template_data['display_name']
                existing.description = template_data.get('description')
                existing.is_system_role = template_data.get('is_system_role', False)
                existing.is_default = template_data.get('is_default', False)
                existing.permissions = template_data.get('permissions', [])
                flag_modified(existing, 'permissions')
                print(f"  ✓ Updated role template: {template_data['name']}")
            else:
                # Create new template
                template = RoleTemplate(
                    name=template_data['name'],
                    display_name=template_data['display_name'],
                    description=template_data.get('description'),
                    is_system_role=template_data.get('is_system_role', False),
                    is_default=template_data.get('is_default', False),
                    permissions=template_data.get('permissions', [])
                )
                db.add(template)
                print(f"  ✓ Created role template: {template_data['name']}")
        
        await db.flush()
        print(f"✓ Processed {len(templates_data)} role templates")

    async def seed_team_role_definitions(db: AsyncSession) -> None:
        """Seed team role definitions from team_role_definitions.yaml"""
        data = load_yaml('team_role_definitions.yaml')
        roles_data = data.get('team_roles', [])
        
        if not roles_data:
            print("⚠️  No team roles found in team_role_definitions.yaml")
            return
        
        print(f"Seeding {len(roles_data)} team role definitions...")
        
        for role_data in roles_data:
            # Check if already exists (system role with tenant_id = None)
            result = await db.execute(
                select(TeamRoleDefinition).where(
                    TeamRoleDefinition.name == role_data['name'],
                    TeamRoleDefinition.tenant_id.is_(None)
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing role
                existing.display_name = role_data['display_name']
                existing.description = role_data.get('description')
                existing.is_system = role_data.get('is_system', False)
                existing.permissions = role_data.get('permissions', [])
                flag_modified(existing, 'permissions')
                print(f"  ✓ Updated team role: {role_data['name']}")
            else:
                # Create new role
                role = TeamRoleDefinition(
                    name=role_data['name'],
                    display_name=role_data['display_name'],
                    description=role_data.get('description'),
                    is_system=role_data.get('is_system', False),
                    tenant_id=None,  # System role
                    permissions=role_data.get('permissions', [])
                )
                db.add(role)
                print(f"  ✓ Created team role: {role_data['name']}")
        
        await db.flush()
        print(f"✓ Processed {len(roles_data)} team role definitions")

    async def update_role_templates_with_domain_permissions(db: AsyncSession) -> None:
        """Add domain permissions to role templates from domain_role_permissions.yaml"""
        data = load_yaml('domain_role_permissions.yaml')
        domain_perms = data.get('domain_permissions', {})
        
        if not domain_perms:
            print("⚠️  No domain permissions found in domain_role_permissions.yaml")
            return
        
        print("Updating role templates with domain permissions...")
        
        for role_name, perms in domain_perms.items():
            result = await db.execute(
                select(RoleTemplate).where(RoleTemplate.name == role_name)
            )
            template = result.scalar_one_or_none()
            
            if not template:
                print(f"  ⚠️  Role template '{role_name}' not found")
                continue
            
            # Add domain permissions if not already present
            current_perms = list(template.permissions)
            changed = False
            
            for perm in perms:
                if perm not in current_perms:
                    current_perms.append(perm)
                    changed = True
            
            if changed:
                template.permissions = current_perms
                flag_modified(template, 'permissions')
                print(f"  ✓ Updated {role_name} with domain permissions")
        
        print("✓ Role templates updated with domain permissions")

    async def update_team_roles_with_domain_permissions(db: AsyncSession) -> None:
        """Add domain permissions to team roles from domain_team_permissions.yaml"""
        data = load_yaml('domain_team_permissions.yaml')
        domain_perms = data.get('domain_permissions', {})
        
        if not domain_perms:
            print("⚠️  No domain permissions found in domain_team_permissions.yaml")
            return
        
        print("Updating team roles with domain permissions...")
        
        for role_name, perms in domain_perms.items():
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
            
            # Replace existing permissions for these resources to ensure correctness
            current_perms = list(role.permissions)
            resources_to_update = {p.get('resource') for p in perms}
            
            # Remove old perms for these resources
            filtered_perms = [p for p in current_perms if p.get('resource') not in resources_to_update]
            
            # Add new perms
            filtered_perms.extend(perms)
            
            if filtered_perms != current_perms:
                role.permissions = filtered_perms
                flag_modified(role, 'permissions')
                print(f"  ✓ Updated {role_name} with domain permissions")
        
        print("✓ Team roles updated with domain permissions")

    async def main():
        """Main seeding function"""
        print("\n" + "="*60)
        print("RBAC and Domain Data Seeding (From YAML)")
        print("="*60 + "\n")
        
        if not database_url:
            print("❌ Error: DATABASE_URL not configured")
            sys.exit(1)
        
        engine = create_async_engine(database_url, echo=False)
        
        try:
            async with AsyncSession(engine) as db:
                async with db.begin():
                    # Seed base RBAC data
                    await seed_actions(db)
                    await seed_resources(db)
                    await seed_domain_resources(db)
                    
                    # Seed role configurations
                    await seed_role_templates(db)
                    await seed_team_role_definitions(db)
                    
                    # Add domain-specific permissions
                    await update_role_templates_with_domain_permissions(db)
                    await update_team_roles_with_domain_permissions(db)
                    
                    # Transaction will auto-commit when exiting this block
                    print("\n✓ All changes committed successfully")
            
            print("\n" + "="*60)
            print("✅ RBAC and domain data seeding complete!")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            await engine.dispose()

    asyncio.run(main())
