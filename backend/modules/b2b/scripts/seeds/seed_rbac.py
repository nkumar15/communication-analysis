import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path to import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from core.config import settings
from modules.b2b.scripts.seeds.rbac_utils import (
    seed_actions, seed_resources, seed_role_templates, seed_team_roles, 
    set_platform_context, seed_plugin_templates
)

# DB Connection
engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    print("📦 Seeding Foundational B2B RBAC...")
    async with SessionLocal() as db:
        await set_platform_context(db)
        config_dir = Path(__file__).parent
        use_case = os.getenv("USE_CASE")
        
        # 1. Foundation Seeding (Always loaded)
        # We always seed foundational actions, resources, and tenant roles (Owner/Admin/etc)
        # to ensure the core platform exists.
        await seed_actions(db, config_dir)
        await seed_resources(db, config_dir, is_system=True, only_system=bool(use_case))
        await seed_role_templates(db, config_dir)
        await seed_plugin_templates(db, config_dir, 'foundation_plugins.yaml')
        
        # 2. SEPARATION LOGIC: Skip Foundation Team Roles if USE_CASE is active
        # Domains (like Bank) define their own specialized business roles.
        if not use_case:
            await seed_team_roles(db, config_dir)
        else:
            print(f"  ⏭️  Skipping foundational generic team roles (Domain {use_case} active)")
            
        await db.commit()
    print("✅ Foundation Seed Complete")

if __name__ == "__main__":
    asyncio.run(main())
