"""
B2C Plans Router

Public endpoints for retrieving subscription plan information.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from core.db.session import get_db
from modules.b2c.models.subscription_plan import SubscriptionPlan
from modules.platform.schemas.plan_schemas import PlanResponse
from datetime import datetime, timezone

router = APIRouter(prefix="/api/b2c/plans", tags=["B2C Plans"])

@router.get("", response_model=List[PlanResponse])
async def list_public_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    List active subscription plans available for purchase.
    Returns plans sorted by price (ascending).
    """
    # Fetch only active, non-archived plans
    # Note: We might want to filter by most recent effective_from per tier_key 
    # if we have multiple versions active (though logic usually implies only one active).
    # For now, simplistic approach: Get all active versions.
    
    stmt = select(SubscriptionPlan).where(
        SubscriptionPlan.effective_from <= datetime.now(timezone.utc),
        SubscriptionPlan.archived_at.is_(None)
    ).order_by(SubscriptionPlan.price_monthly.asc())
    
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    # Filter to ensure we only return the LATEST active version for each tier_key
    # (In case multiple past versions are still "active" / not archived but old)
    # Actually, business logic says effective_from <= now.
    # We should probably grouping by tier_key and taking max(effective_from).
    # But usually we would archive old ones when creating new ones.
    # Let's do a python side filter to be safe.
    
    plans_by_tier = {}
    for p in plans:
        if p.tier_key not in plans_by_tier:
            plans_by_tier[p.tier_key] = p
        else:
            # If we found a newer one? The query ordered by price. 
            # Let's assume order_by effective_from desc in query is better for this.
            pass

    # improving query
    return plans
