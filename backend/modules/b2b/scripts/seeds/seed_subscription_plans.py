"""
Seed B2B Subscription Plans
"""
import asyncio
import os
import sys
import yaml
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

# Setup path to import from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from core.config import settings
from modules.b2b.models.subscription_plan import B2BSubscriptionPlan

def load_plans_from_yaml():
    yaml_path = Path(__file__).parent / 'foundation_subscription_plans.yaml'
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
        # We now ALWAYS seed foundational plans. 
        # Domains will overlay their specific tiers if they provide them.
        print("Seeding Foundational B2B Plans...")
        
        # Set RLS context for seeding (simulate platform admin)
        await db.execute(text("SELECT set_config('app.current_user_role', 'platform_admin', false)"))
        
        raw_plans = load_plans_from_yaml()
        
        # Define hierarchy order
        hierarchy = ['starter', 'professional', 'enterprise']
        
        # Sort plans by hierarchy to ensure correct processing order
        plans_map = {p['tier_key']: p for p in raw_plans}
        sorted_plans = []
        for key in hierarchy:
            if key in plans_map:
                sorted_plans.append(plans_map[key])
        
        # Accumulated state
        inherited_features = {}
        inherited_limits = {}

        for plan_data in sorted_plans:
            tier = plan_data['tier_key']
            print(f"Processing {tier}...")

            # 1. Merge Features (Deep Merge + List Union)
            current_features = plan_data.get('features', {})
            # Start with a copy of inherited
            final_features = deep_merge_features(inherited_features, current_features)
            
            # Update inheritance for next tier
            inherited_features = final_features.copy()
            
            # 2. Merge Limits (Simple Override)
            # Logic: If defined in current, use current. Else use inherited.
            current_limits = plan_data.get('limits', {})
            final_limits = inherited_limits.copy()
            final_limits.update(current_limits)
            
            inherited_limits = final_limits.copy()

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
                    limits=final_limits,
                    features=final_features,
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
                plan.limits = final_limits
                plan.features = final_features
                plan.contact_required = plan_data.get('contact_required', False)
                plan.provider_config = provider_config
                print(f"  ↻ Updated plan: {plan_data['name']}")
                
                # Debug Output
                import json
                print(f"    -> Final Features: {json.dumps(final_features, sort_keys=True)}")
        
        await db.commit()
    
    print("✅ B2B Plans Seeded")

def deep_merge_features(base, override):
    """
    Merge override features into base features.
    - Dicts: Recursive merge
    - Lists: Union (Set-based)
    - Scalars: Override
    """
    import copy
    result = copy.deepcopy(base)
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_features(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # Union for lists (e.g. plugins)
            base_set = set(result[key])
            for item in value:
                base_set.add(item)
            result[key] = sorted(list(base_set))
        else:
            # Scalar or type mismatch -> Override
            result[key] = value
            
    return result

if __name__ == "__main__":
    asyncio.run(seed_b2b_plans())

if __name__ == "__main__":
    asyncio.run(seed_b2b_plans())
