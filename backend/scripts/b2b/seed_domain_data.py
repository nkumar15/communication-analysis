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
    from core.database import database_url
    from services.b2b.models.rbac import Resource
    from services.b2b.models.role_template import RoleTemplate

    async def seed_domain_resources(db: AsyncSession) -> None:
        """Seed domain-specific resources"""
        result = await db.execute(select(Resource).where(Resource.name == 'farmers'))
        if result.scalar_one_or_none():
            print("✓ Domain resources already seeded")
            return
        
        print("Seeding domain resources...")
        domain_resources = [
            Resource(
                name='farmers',
                display_name='Farmer Management',
                category='domain',
                description='Farmer onboarding and data management'
            ),
        ]
        db.add_all(domain_resources)
        await db.commit()
        print(f"✓ Seeded {len(domain_resources)} domain resources")

    async def seed_domain_role_templates(db: AsyncSession) -> None:
        """Seed domain-specific role templates"""
        result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'field_manager'))
        if result.scalar_one_or_none():
            print("✓ Domain role templates already seeded")
            return
        
        print("Seeding domain role templates...")
        domain_templates = [
            RoleTemplate(
                name='field_manager',
                display_name='Field Manager',
                description='Manages field operations and farmer relationships',
                is_system_role=False,
                is_default=True,  # Agriculture deployment: core role for this business
                permissions=[
                    {"resource": "farmers", "actions": ["read", "write", "delete"]},
                    {"resource": "users", "actions": ["read"]},
                ]
            ),
            RoleTemplate(
                name='field_agent',
                display_name='Field Agent',
                description='Limited access for field operations',
                is_system_role=False,
                is_default=True,  # Agriculture deployment: core role for this business
                permissions=[
                    {"resource": "farmers", "actions": ["read", "write"]},
                ]
            ),
        ]
        db.add_all(domain_templates)
        await db.commit()
        print(f"✓ Seeded {len(domain_templates)} domain role templates")

    async def main():
        """Main seeding function"""
        print("\n" + "="*50)
        print("Domain Data Seeding")
        print("="*50 + "\n")
        
        if not database_url:
            print("❌ Error: DATABASE_URL not configured")
            sys.exit(1)
        
        engine = create_async_engine(database_url, echo=False)
        
        try:
            async with AsyncSession(engine) as db:
                await seed_domain_resources(db)
                await seed_domain_role_templates(db)
                
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
