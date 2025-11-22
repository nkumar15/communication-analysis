#!/usr/bin/env python3
"""
Simple migration runner
"""
import asyncio
import asyncpg
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings


async def run_migrations():
    """Run all SQL migrations in order"""
    migrations_dir = Path(__file__).parent
    
    # Connect to database
    conn = await asyncpg.connect(settings.database_url)
    
    try:
        # Get all migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            print(f"Running migration: {migration_file.name}")
            sql = migration_file.read_text()
            await conn.execute(sql)
            print(f"✓ Completed: {migration_file.name}")
        
        print("\n✓ All migrations completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
