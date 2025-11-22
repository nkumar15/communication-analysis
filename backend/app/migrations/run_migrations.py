#!/usr/bin/env python3
"""
Simple migration runner with tracking
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
        # Create migrations tracking table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Get list of already applied migrations
        applied = await conn.fetch("SELECT filename FROM schema_migrations")
        applied_files = {row['filename'] for row in applied}
        
        # Get all migration files
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        migrations_applied = 0
        for migration_file in migration_files:
            if migration_file.name in applied_files:
                print(f"⏭️  Skipping (already applied): {migration_file.name}")
                continue
            
            print(f"🔄 Running migration: {migration_file.name}")
            sql = migration_file.read_text()
            
            # Run migration in a transaction
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    migration_file.name
                )
            
            print(f"✅ Completed: {migration_file.name}")
            migrations_applied += 1
        
        if migrations_applied == 0:
            print("\n✓ No new migrations to apply. Database is up to date!")
        else:
            print(f"\n✓ Successfully applied {migrations_applied} new migration(s)!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())
