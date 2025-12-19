"""
Seed Platform Permissions

Populates platform_permissions table with granular permissions for system roles.
Creates roles if they don't exist (self-contained).
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

async def ensure_role_exists(db: AsyncSession, role_name: str, role_config: dict):
    """Ensure role exists, create if not (system-level, no tenant)"""
    result = await db.execute(
        select(PlatformRole).where(PlatformRole.name == role_name)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        # Get role metadata from YAML or use defaults
        display_name = role_config.get('display_name', role_name.replace('_', ' ').title())
        description = role_config.get('description', f"{display_name} role")
        
        role = PlatformRole(
            name=role_name,
            display_name=display_name,
            description=description,
            is_system_role=True
        )
        db.add(role)
        await db.flush()
        await db.refresh(role)
        print(f"   ✅ Created role: {display_name}")
    
    return role

async def seed_permissions():
    print("🌱 Seeding Platform Permissions...")
    
    role_permissions = load_role_permissions()
    
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Process each role and its permissions
        for role_name, role_config in role_permissions.items():
            print(f"\n🔐 Processing {role_name}...")
            
            # Ensure role exists (system-level, no tenant)
            role = await ensure_role_exists(db, role_name, role_config)
            
            # Add permissions
            perms = role_config.get('permissions', [])
            current_count = 0
            
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

