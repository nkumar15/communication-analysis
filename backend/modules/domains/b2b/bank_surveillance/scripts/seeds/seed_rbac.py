import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path to import from backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from core.config import settings
from modules.b2b.scripts.seeds.rbac_utils import (
    seed_actions, seed_resources, seed_team_roles, apply_permission_overlays, seed_plugin_templates, set_platform_context
)

# DB Connection
engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    print("📦 Seeding Bank Surveillance RBAC...")
    async with SessionLocal() as db:
        await set_platform_context(db)
        config_dir = Path(__file__).parent
        # Seed domain-specific logic
        await seed_actions(db, config_dir)
        await seed_resources(db, config_dir)
        await seed_plugin_templates(db, config_dir)
        await seed_team_roles(db, config_dir)
        await apply_permission_overlays(db, config_dir)
        await db.commit()
    print("✅ Domain Seed Complete")

if __name__ == "__main__":
    asyncio.run(main())
