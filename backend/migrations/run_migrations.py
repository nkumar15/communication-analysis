#!/usr/bin/env python3
"""
Modular Migration Runner with Product Selection

Supports running migrations for specific products based on ENABLED_PRODUCTS env var.

Usage:
    ENABLED_PRODUCTS=b2b python run_migrations.py    # B2B (default)
"""
import asyncio
import asyncpg
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings

# Default: B2B enabled for development
DEFAULT_PRODUCTS = "b2b"


async def run_migrations():
    """Run migrations for enabled products in order"""
    migrations_dir = Path(__file__).parent
    
    # Get enabled products from environment
    enabled_products = os.getenv("ENABLED_PRODUCTS", DEFAULT_PRODUCTS).split(",")
    enabled_products = [p.strip() for p in enabled_products]
    
    print(f"🔧 Enabled products: {enabled_products}")
    
    # Define migration order: core first, then products
    # Core always runs, then products in dependency order
    migration_order = ["core"]

    # Add enabled products
    if "b2b" in enabled_products:
        migration_order.append("b2b")
    
    # Remove duplicates while preserving order
    seen = set()
    migration_order = [x for x in migration_order if not (x in seen or seen.add(x))]
    
    print(f"📋 Migration order: {migration_order}")
    
    # Connect to database
    conn = await asyncpg.connect(settings.database_url)
    
    try:
        # Create migrations tracking table if it doesn't exist
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                product VARCHAR(50),
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add product column if it doesn't exist (for backwards compatibility)
        await conn.execute("""
            DO $$ 
            BEGIN
                ALTER TABLE public.schema_migrations ADD COLUMN IF NOT EXISTS product VARCHAR(50);
            EXCEPTION WHEN duplicate_column THEN
                NULL;
            END $$;
        """)
        
        # Get list of already applied migrations
        applied = await conn.fetch("SELECT filename FROM public.schema_migrations")
        applied_files = {row['filename'] for row in applied}
        
        migrations_applied = 0
        
        for product in migration_order:
            product_dir = migrations_dir / product
            
            if not product_dir.exists():
                print(f"⚠️  Product directory not found: {product}")
                continue
            
            # Get all migration files for this product
            migration_files = sorted(product_dir.glob("*.sql"))
            
            for migration_file in migration_files:
                # Create unique filename with product prefix
                unique_name = f"{product}/{migration_file.name}"
                
                if unique_name in applied_files:
                    print(f"⏭️  Skipping (already applied): {unique_name}")
                    continue
                
                print(f"🔄 Running migration: {unique_name}")
                sql = migration_file.read_text()
                
                # Run migration in a transaction
                async with conn.transaction():
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO public.schema_migrations (filename, product) VALUES ($1, $2)",
                        unique_name, product
                    )
                
                print(f"✅ Completed: {unique_name}")
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
