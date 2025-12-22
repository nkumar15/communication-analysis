"""
Seed B2C Subscription Plans
(Refreshed)
"""
import sys
import os
import yaml
import asyncio
from pathlib import Path
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm.attributes import flag_modified

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from core.db.session import database_url
from services.b2c.models.subscription_plan import SubscriptionPlan

YAML_DIR = Path(__file__).parent / "data"

def load_yaml(filename: str) -> dict:
    filepath = YAML_DIR / filename
    if not filepath.exists():
        print(f"⚠️  Warning: {filename} not found")
        return {}
    
    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}

async def fetch_stripe_price(price_id: str, default: int) -> int:
    """Fetch price unit amount from Stripe, fallback to default."""
    if not price_id:
        return default
        
    try:
        import stripe
        from core.config import settings
        
        if not settings.stripe_secret_key:
            return default
            
        stripe.api_key = settings.stripe_secret_key
        
        # Stripe calls are blocking, run in executor
        loop = asyncio.get_event_loop()
        price = await loop.run_in_executor(None, lambda: stripe.Price.retrieve(price_id))
        
        print(f"  ✓ Fetched price for {price_id}: {price.unit_amount/100:.2f} {price.currency.upper()}")
        return price.unit_amount
        
    except Exception as e:
        print(f"  ⚠️  Failed to fetch price {price_id}: {e}")
        return default

async def seed_plans(db: AsyncSession) -> None:
    data = load_yaml('subscription_plans.yaml')
    plans_data = data.get('plans', [])
    
    if not plans_data:
        print("⚠️  No plans found in subscription_plans.yaml")
        return
    
    print(f"Seeding {len(plans_data)} subscription plans...")
    
    for plan_data in plans_data:
        tier = plan_data['tier']
        name = tier.title()
        
        # Determine provider
        provider = plan_data.get('provider', 'stripe')
        print(f"Processing plan: {tier} (Provider: {provider})")
        
        provider_config = {}
        price_monthly = 0
        price_yearly = 0
        
        if provider == 'stripe':
            # Fetch Stripe prices
            from core.config import settings
            
            # We need to map tier to config keys
            # premium -> stripe_price_premium_...
            # ultimate -> stripe_price_ultimate_...
            
            # Monthly
            monthly_attr = f"stripe_price_{tier}_monthly"
            monthly_price_id = getattr(settings, monthly_attr, None)
            
            if not monthly_price_id:
                 print(f"Warning: No monthly price configured for {tier}")
                 
            # Yearly
            yearly_attr = f"stripe_price_{tier}_yearly"
            yearly_price_id = getattr(settings, yearly_attr, None)

            # Fetch amounts
            # Note: We fetch amount from monthly usually
            
            if monthly_price_id:
                price_monthly = await fetch_stripe_price(monthly_price_id, default=1500 if tier=='premium' else 5000)
            if yearly_price_id:
                price_yearly = await fetch_stripe_price(yearly_price_id, default=15000 if tier=='premium' else 50000)
                
            provider_config = {
                'stripe': {
                    'monthly_price_id': monthly_price_id,
                    'yearly_price_id': yearly_price_id
                }
            }
        
        elif provider == 'razorpay':
            # Placeholder logic for Razorpay
            # We would fetch from settings e.g. razorpay_plan_id_premium
            # For now just set placeholder
            provider_config = {
                'razorpay': {
                    'plan_id': f"plan_{tier}_placeholder"
                }
            }
            price_monthly = 9999
            price_yearly = 99999
        
        else:
             print(f"Unknown provider: {provider}")
             continue

        # Check if plan exists (by tier AND provider?)
        # Usually tier is unique? 
        # If we want same tier on multiple providers, we need composite key or different tier names?
        # Current schema has unique tier_key. 
        # So 'premium' can only be on one provider?
        # Or we change schema to allow multiple providers for same tier?
        # For now, let's assume one active provider per tier for the seed.
        
        # Check active plan version
        stmt = select(SubscriptionPlan).where(
            SubscriptionPlan.tier_key == tier,
            SubscriptionPlan.archived_at.is_(None)
        ).order_by(SubscriptionPlan.effective_from.desc())
        
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing plan (simplified: just update fields for now in dev/greenfield reset)
            # In prod we might create new version if critical fields change
            changes = False
            if existing.limits != plan_data['limits']:
                existing.limits = plan_data['limits']
                changes = True
            
            if existing.features != plan_data['features']:
                existing.features = plan_data['features']
                changes = True
                
            if existing.provider_config != provider_config:
                existing.provider_config = provider_config
                changes = True
                
            if changes:
                flag_modified(existing, 'limits')
                flag_modified(existing, 'features')
                flag_modified(existing, 'provider_config')
                print(f"  ✓ Updated plan: {tier}")
            else:
                print(f"  - No changes for: {tier}")
        else:
            # Create new plan
            plan = SubscriptionPlan(
                tier_key=tier,
                name=name,
                description=f"{name} Tier Subscription",
                price_monthly=price_monthly,
                price_yearly=price_yearly,
                limits=plan_data['limits'],
                features=plan_data['features'],
                provider_config=provider_config
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
                # Bypass RLS for seeding
                await db.execute(text("SET app.is_platform_admin = 'true'"))
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
