#!/usr/bin/env python3
"""
Seed B2C Subscription Plans
"""
import sys
import os
import yaml
import asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm.attributes import flag_modified

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from core.database import database_url
from services.b2c.models.subscription_plan import SubscriptionPlan

YAML_DIR = Path(__file__).parent / "data"

def load_yaml(filename: str) -> dict:
    filepath = YAML_DIR / filename
    if not filepath.exists():
        print(f"⚠️  Warning: {filename} not found")
        return {}
    
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}

async def seed_plans(db: AsyncSession) -> None:
    data = load_yaml('subscription_plans.yaml')
    plans_data = data.get('plans', [])
    
    if not plans_data:
        print("⚠️  No plans found in subscription_plans.yaml")
        return
    
    print(f"Seeding {len(plans_data)} subscription plans...")
    
    for plan_data in plans_data:
        tier = plan_data['tier']
        
        result = await db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.tier == tier)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing plan
            if existing.limits != plan_data['limits']:
                existing.limits = plan_data['limits']
                flag_modified(existing, 'limits')
            
            if existing.features != plan_data['features']:
                existing.features = plan_data['features']
                flag_modified(existing, 'features')
                
            print(f"  ✓ Updated plan: {tier}")
        else:
            # Create new plan
            plan = SubscriptionPlan(
                tier=tier,
                limits=plan_data['limits'],
                features=plan_data['features']
            )
            db.add(plan)
            print(f"  ✓ Created plan: {tier}")
            
    await db.flush()

async def main():
    print("\n" + "="*60)
    print("B2C Subscription Plans Seeding")
    print("="*60 + "\n")
    
    if not database_url:
        print("❌ Error: DATABASE_URL not configured")
        sys.exit(1)
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with AsyncSession(engine) as db:
            async with db.begin():
                await seed_plans(db)
                print("\n✓ All changes committed successfully")
        
        print("\n" + "="*60)
        print("✅ Seeding complete!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
