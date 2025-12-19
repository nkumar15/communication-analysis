"""
Seed Platform Permissions

Populates platform_permissions table with granular permissions for system roles.
Usage: python scripts/platform/seed_platform_permissions.py
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from services.platform.models import PlatformRole, PlatformPermission
from core.config import settings

import yaml

def load_role_permissions():
    """Load role permissions from YAML file"""
    yaml_path = os.path.join(os.path.dirname(__file__), 'role_permissions.yaml')
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('roles', {})
    except FileNotFoundError:
        print(f"❌ Error: {yaml_path} not found.")
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"❌ Error parsing YAML: {exc}")
        sys.exit(1)

async def seed_permissions():
    print("🌱 Seeding Platform Permissions...")
    
    role_permissions = load_role_permissions()
    
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Get system roles
        result = await db.execute(select(PlatformRole))
        roles = result.scalars().all()
        
        role_map = {r.name: r for r in roles}
        
        for role_name, perms in role_permissions.items():
            role = role_map.get(role_name)
            if not role:
                print(f"⚠️ Role {role_name} not found, ask to run seed_system_tenant.py first")
                continue
                
            print(f"\n🔐 Processing {role_name} (ID: {role.id})...")
            
            current_count = 0
            # Delete existing to reset/update
            # In a real prod migration we might valid difference, but for seed it's safer to clear & re-add
            # Or check existence. Let's check existence to be safe.
            
            for perm in perms:
                # Check if exists
                stmt = select(PlatformPermission).where(
                    PlatformPermission.platform_role_id == role.id,
                    PlatformPermission.resource == perm['resource'],
                    PlatformPermission.action == perm['action']
                )
                existing = await db.scalar(stmt)
                
                if not existing:
                    new_perm = PlatformPermission(
                        platform_role_id=role.id,
                        resource=perm['resource'],
                        action=perm['action']
                    )
                    db.add(new_perm)
                    current_count += 1
                    print(f"   + Added: {perm['resource']}:{perm['action']}")
                else:
                    print(f"   . Exists: {perm['resource']}:{perm['action']}")
            
            if current_count > 0:
                await db.commit()
                print(f"   ✅ Added {current_count} permissions")
            else:
                print("   ✨ Up to date")

    await engine.dispose()
    print("\n✅ Permissions seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_permissions())
