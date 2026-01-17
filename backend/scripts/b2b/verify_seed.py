#!/usr/bin/env python3
"""
Verify B2B Seed Data

This script checks that all required seed data exists in the database.
Run after seeding to ensure everything is properly initialized.

Exit codes:
  0 - All checks passed
  1 - One or more checks failed
"""

if __name__ == "__main__":
    # Fix sys.path BEFORE any imports to avoid platform.py collision
    import sys
    import os
    
    # Remove scripts directory from path to avoid shadowing stdlib
    sys.path = [p for p in sys.path if not p.endswith('/scripts/b2b') and not p.endswith('/scripts') and p != '']
    
    # Ensure /app is first in path for imports
    if '/app' not in sys.path:
        sys.path.insert(0, '/app')
    
    # Now safe to import everything else
    import asyncio
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from core.db.session import database_url
    from modules.b2b.models.role_template import RoleTemplate
    from modules.b2b.models.rbac import Resource, Action
    from modules.b2b.models.subscription_plan import B2BSubscriptionPlan

    # Color codes for terminal output
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    async def verify_seeds():
        """Verify all required seed data exists."""
        
        # Create async engine
        db_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        checks = []
        
        async with async_session() as db:
            # 1. Check role_templates
            result = await db.execute(select(func.count()).select_from(RoleTemplate))
            role_template_count = result.scalar()
            checks.append(("Role Templates (b2b.role_templates)", role_template_count, role_template_count > 0))
            
            # 2. Check resources
            result = await db.execute(select(func.count()).select_from(Resource))
            resource_count = result.scalar()
            checks.append(("Resources (b2b.resources)", resource_count, resource_count > 0))
            
            # 3. Check actions
            result = await db.execute(select(func.count()).select_from(Action))
            action_count = result.scalar()
            checks.append(("Actions (b2b.actions)", action_count, action_count > 0))
            
            # 4. Check subscription plans
            result = await db.execute(select(func.count()).select_from(B2BSubscriptionPlan))
            plan_count = result.scalar()
            checks.append(("Subscription Plans (b2b.subscription_plans)", plan_count, plan_count > 0))
        
        await engine.dispose()
        
        # Print results
        print("\n" + "=" * 60)
        print("B2B SEED VERIFICATION REPORT")
        print("=" * 60)
        
        all_passed = True
        for name, count, passed in checks:
            status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
            count_str = f"({count} rows)"
            print(f"  {status}  {name} {count_str}")
            if not passed:
                all_passed = False
        
        print("=" * 60)
        
        if all_passed:
            print(f"{GREEN}All seed verification checks passed!{RESET}\n")
            return 0
        else:
            print(f"{RED}Some seed verification checks failed!{RESET}")
            print(f"{YELLOW}Run 'make seed-all USE_CASE=<your_use_case>' to fix.{RESET}\n")
            return 1

    exit_code = asyncio.run(verify_seeds())
    sys.exit(exit_code)
