#!/usr/bin/env python3
"""
Domain-Specific Data Seeding Script

Seeds domain-specific resources and role templates.
Run this after migrations to add business-specific data.
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
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm.attributes import flag_modified
    from core.database import database_url
    from services.b2b.models.rbac import Resource
    from services.b2b.models.role_template import RoleTemplate

    async def seed_domain_resources(db: AsyncSession) -> None:
        """
        Seed DOMAIN-SPECIFIC resources (Task Management)
        
        These resources are for the task management and collaboration domain.
        For a different domain (e.g., ecommerce), replace with domain-appropriate 
        resources like 'products', 'orders', 'inventory', etc.
        """
        result = await db.execute(select(Resource).where(Resource.name == 'projects'))
        if result.scalar_one_or_none():
            print("✓ Domain resources already seeded")
            return
        
        print("Seeding domain resources (Task Management)...")
        domain_resources = [
            Resource(
                name='projects',
                display_name='Projects',
                category='Domain',
                description='Project management and team collaboration'
            ),
            Resource(
                name='tasks',
                display_name='Tasks',
                category='Domain',
                description='Task tracking and assignment'
            ),
            Resource(
                name='comments',
                display_name='Comments',
                category='Domain',
                description='Task comments and discussions'
            ),
        ]
        db.add_all(domain_resources)
        await db.commit()
        print(f"✓ Seeded {len(domain_resources)} domain resources")

    async def seed_domain_role_templates(db: AsyncSession) -> None:
        """
        Update existing role templates with domain permissions
        
        Adds projects, tasks, and comments permissions to standard roles
        """
        print("Updating role templates with domain permissions...")
        
        # Update owner role
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'owner'))
        owner = result.scalar_one_or_none()
        if owner:
            # Add domain permissions if not already present
            domain_perms = [
                {"resource": "projects", "actions": ["read", "write", "delete"]},
                {"resource": "tasks", "actions": ["read", "write", "delete"]},
                {"resource": "comments", "actions": ["read", "write", "delete"]},
            ]
            for perm in domain_perms: 
                if perm not in owner.permissions:
                    owner.permissions.append(perm)
            flag_modified(owner, 'permissions')  # Force SQLAlchemy to detect JSONB change
            await db.commit()
            print("✓ Updated owner role with domain permissions")
        
        # Update admin role
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'admin'))
        admin = result.scalar_one_or_none()
        if admin:
            domain_perms = [
                {"resource": "projects", "actions": ["read", "write", "delete"]},
                {"resource": "tasks", "actions": ["read", "write", "delete"]},
                {"resource": "comments", "actions": ["read", "write", "delete"]},
            ]
            for perm in domain_perms:
                if perm not in admin.permissions:
                    admin.permissions.append(perm)
            flag_modified(admin, 'permissions')
            await db.commit()
            print("✓ Updated admin role with domain permissions")
        
        # Update member role
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'member'))
        member = result.scalar_one_or_none()
        if member:
            domain_perms = [
                {"resource": "projects", "actions": ["read"]},
                {"resource": "tasks", "actions": ["read", "write"]},
                {"resource": "comments", "actions": ["read", "write", "delete"]},  # delete for own comments
            ]
            for perm in domain_perms:
                if perm not in member.permissions:
                    member.permissions.append(perm)
            flag_modified(member, 'permissions')
            await db.commit()
            print("✓ Updated member role with domain permissions")
        
        # Update viewer role (read-only access)
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'viewer'))
        viewer = result.scalar_one_or_none()
        if viewer:
            domain_perms = [
                {"resource": "projects", "actions": ["read"]},
                {"resource": "tasks", "actions": ["read"]},
                {"resource": "comments", "actions": ["read"]},
            ]
            for perm in domain_perms:
                if perm not in viewer.permissions:
                    viewer.permissions.append(perm)
            flag_modified(viewer, 'permissions')
            await db.commit()
            print("✓ Updated viewer role with domain permissions")

    async def seed_team_role_permissions(db: AsyncSession) -> None:
        """
        Update default TEAM roles with domain permissions
        This is where we implement GRANULAR control (projects vs tasks)
        """
        print("Updating team roles with domain permissions...")
        from services.b2b.models.team_role_definition import TeamRoleDefinition
        
        # 1. Team Manager (Full Access)
        result = await db.execute(select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == 'team_manager',
            TeamRoleDefinition.tenant_id.is_(None) # System role
        ))
        team_manager = result.scalar_one_or_none()
        if team_manager:
            domain_perms = [
                {"resource": "projects", "actions": ["read", "write", "delete"]},
                {"resource": "tasks", "actions": ["read", "write", "delete"]},
                {"resource": "comments", "actions": ["read", "write", "delete"]},
            ]
            # Merge permissions
            current_perms = list(team_manager.permissions)
            changed = False
            for perm in domain_perms:
                if perm not in current_perms:
                    current_perms.append(perm)
                    changed = True
            
            if changed:
                team_manager.permissions = current_perms
                flag_modified(team_manager, 'permissions')
                await db.commit()
                print("✓ Updated team_manager with domain permissions")

        # 2. Team Contributor (The Key Change: Read-only Projects, Write Tasks)
        result = await db.execute(select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == 'team_contributor',
            TeamRoleDefinition.tenant_id.is_(None)
        ))
        contributor = result.scalar_one_or_none()
        if contributor:
            domain_perms = [
                {"resource": "projects", "actions": ["read"]}, # Read only!
                {"resource": "tasks", "actions": ["read", "write"]},
                {"resource": "comments", "actions": ["read", "write", "delete"]}, 
            ]
            # Force overwrite checks for system roles to ensure correctness
            # We want to ensure these EXACT permissions are present.
            # Merging is fine, but let's be safe.
            current_perms = list(contributor.permissions)
            
            # Remove any existing perms for these resources to avoid duplicates/conflicts
            resources_to_update = {"projects", "tasks", "comments"}
            filtered_perms = [p for p in current_perms if p.get("resource") not in resources_to_update]
            
            # Add new perms
            filtered_perms.extend(domain_perms)
            
            if filtered_perms != current_perms:
                contributor.permissions = filtered_perms
                flag_modified(contributor, 'permissions')
                await db.commit()
                print("✓ Updated team_contributor with granular domain permissions")

        # 3. Team Reader (Read Only)
        result = await db.execute(select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == 'team_reader',
            TeamRoleDefinition.tenant_id.is_(None)
        ))
        reader = result.scalar_one_or_none()
        if reader:
            domain_perms = [
                {"resource": "projects", "actions": ["read"]},
                {"resource": "tasks", "actions": ["read"]},
                {"resource": "comments", "actions": ["read"]},
            ]
            
            current_perms = list(reader.permissions)
            filtered_perms = [p for p in current_perms if p.get("resource") not in {"projects", "tasks", "comments"}]
            filtered_perms.extend(domain_perms)
            
            if filtered_perms != current_perms:
                reader.permissions = filtered_perms
                flag_modified(reader, 'permissions')
                await db.commit()
                print("✓ Updated team_reader with domain permissions")


    async def main():
        """Main seeding function"""
        print("\n" + "="*50)
        print("Domain Data Seeding - Task Management")
        print("="*50 + "\n")
        
        if not database_url:
            print("❌ Error: DATABASE_URL not configured")
            sys.exit(1)
        
        engine = create_async_engine(database_url, echo=False)
        
        try:
            async with AsyncSession(engine) as db:
                await seed_domain_resources(db)
                await seed_domain_role_templates(db)
                await seed_team_role_permissions(db)
                
            print("\n" + "="*50)
            print("✅ Domain data seeding complete!")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            await engine.dispose()

    asyncio.run(main())
