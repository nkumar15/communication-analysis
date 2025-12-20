"""
Seed B2B Subscription Plans
"""
import asyncio
import os
import sys
import yaml
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append('/app')

from core.config import settings
from services.b2b.models.subscription_plan import B2BSubscriptionPlan

def load_plans_from_yaml():
    yaml_path = os.path.join(os.path.dirname(__file__), 'data/subscription_plans.yaml')
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    return data.get('plans', [])

async def seed_b2b_plans():
    database_url = settings.database_url
    if not database_url:
        print("❌ Error: DATABASE_URL not configured")
        return
        
    # Ensure using async driver
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Seeding B2B Plans...")
        
        # Set RLS context for seeding (simulate platform admin)
        await db.execute(text("SELECT set_config('app.current_user_role', 'platform_admin', false)"))
        
        plans = load_plans_from_yaml()
        
        for plan_data in plans:
            tier = plan_data['tier_key']
            
            # Construct provider config from settings
            stripe_config = {}
            if tier == 'starter':
                stripe_config = {
                    'monthly_price_id': settings.stripe_b2b_price_starter_monthly,
                    'yearly_price_id': settings.stripe_b2b_price_starter_yearly
                }
            elif tier == 'professional':
                stripe_config = {
                    'monthly_price_id': settings.stripe_b2b_price_professional_monthly,
                    'yearly_price_id': settings.stripe_b2b_price_professional_yearly
                }
            # Enterprise doesn't have public price IDs
            
            # Filter out None values
            provider_config = {
                'stripe': {k: v for k, v in stripe_config.items() if v}
            }

            stmt = select(B2BSubscriptionPlan).where(B2BSubscriptionPlan.tier_key == plan_data['tier_key'])
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                new_plan = B2BSubscriptionPlan(
                    tier_key=plan_data['tier_key'],
                    name=plan_data['name'],
                    description=plan_data['description'],
                    base_price_monthly=plan_data['base_price_monthly'],
                    base_price_yearly=plan_data['base_price_yearly'],
                    per_seat_price_monthly=plan_data['per_seat_price_monthly'],
                    per_seat_price_yearly=plan_data['per_seat_price_yearly'],
                    limits=plan_data['limits'],
                    features=plan_data['features'],
                    contact_required=plan_data.get('contact_required', False),
                    provider_config=provider_config
                )
                db.add(new_plan)
                print(f"  ✓ Created plan: {plan_data['name']}")
            else:
                # Update existing plan
                plan = existing
                plan.name = plan_data['name']
                plan.description = plan_data['description']
                plan.base_price_monthly = plan_data['base_price_monthly']
                plan.base_price_yearly = plan_data['base_price_yearly']
                plan.per_seat_price_monthly = plan_data['per_seat_price_monthly']
                plan.per_seat_price_yearly = plan_data['per_seat_price_yearly']
                plan.limits = plan_data['limits']
                plan.features = plan_data['features']
                plan.contact_required = plan_data.get('contact_required', False)
                plan.provider_config = provider_config
                print(f"  ↻ Updated plan: {plan_data['name']}")
        
        await db.commit()
    
    print("✅ B2B Plans Seeded")

if __name__ == "__main__":
    asyncio.run(seed_b2b_plans())
