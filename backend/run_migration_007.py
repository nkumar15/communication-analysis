import asyncio
import os
import sys
from sqlalchemy import text

# Add current directory to path so we can import app
sys.path.append(os.getcwd())

from app.database import engine

async def run_migration():
    migration_file = 'app/migrations/007_migrate_legacy_roles.sql'
    print(f"Reading migration file: {migration_file}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    async with engine.begin() as conn:
        # Split by semicolon to run multiple statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for stmt in statements:
            print(f"Executing: {stmt[:50]}...")
            await conn.execute(text(stmt))
            
    print("Migration 007 completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
