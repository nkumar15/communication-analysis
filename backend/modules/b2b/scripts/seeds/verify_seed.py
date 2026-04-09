import asyncio
import sys
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path to import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from core.config import settings
from modules.b2b.scripts.seeds.verify_utils import check_foundation, print_report, RED, YELLOW, RESET

# DB Connection
engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"))
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with SessionLocal() as db:
        checks = await check_foundation(db)
        all_passed = print_report("B2B FOUNDATION SEED VERIFICATION", checks)
        
        if not all_passed:
            print(f"{RED}Some foundational seed checks failed!{RESET}")
            print(f"{YELLOW}Run 'make seed-all' to fix.{RESET}")
            sys.exit(1)
        
    print("✅ Foundation Verification Complete")

if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
