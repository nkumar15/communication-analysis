import os
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from modules.b2b.models.role_template import RoleTemplate
from modules.b2b.models.rbac import Resource, Action

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

async def check_foundation(db: AsyncSession) -> List[tuple]:
    """Check required foundational B2B seed data."""
    checks = []
    
    # 1. Check role_templates (Always expect foundational 4 + any domain ones)
    result = await db.execute(select(func.count()).select_from(RoleTemplate))
    count = result.scalar()
    checks.append(("Role Templates (b2b.role_templates)", count, count >= 4))
    
    # 2. Check resources (Always expect foundational 10 system + any domain ones)
    result = await db.execute(select(func.count()).select_from(Resource))
    count = result.scalar()
    checks.append(("Resources (b2b.resources)", count, count >= 10))
    
    # 3. Check actions (Foundation has 7 core actions)
    result = await db.execute(select(func.count()).select_from(Action))
    count = result.scalar()
    checks.append(("Actions (b2b.actions)", count, count >= 7))

    return checks

def print_report(title: str, checks: List[tuple]) -> bool:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    
    all_passed = True
    for name, count, passed in checks:
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        count_str = f"({count} rows)"
        print(f"  {status}  {name} {count_str}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    return all_passed
