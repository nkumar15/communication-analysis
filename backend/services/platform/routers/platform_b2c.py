"""
Platform B2C API Router - Personal Workspace Management
All B2C-related endpoints under /api/platform/b2c/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from core.database import get_db
from core.database import get_db
from services.platform.middleware.platform_auth import verify_platform_admin
from services.b2c.models.subscription_plan import SubscriptionPlan
from services.platform.schemas.plan_schemas import PlanCreate, PlanResponse, PlanUpdate
from sqlalchemy import select, desc
from datetime import datetime
from uuid import UUID
from typing import List

router = APIRouter(
    prefix="/api/platform/b2c",
    tags=["platform-b2c"]
)

# --- Schemas ---

class B2CStats(BaseModel):
    total_workspaces: int
    personal_workspaces: int
    team_workspaces: int
    total_users: int


# --- Endpoints ---

@router.get("/stats", response_model=B2CStats)
async def get_b2c_stats(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get B2C platform statistics (personal workspaces)"""
    
    try:
        # Use SECURITY DEFINER function to bypass RLS for platform admin
        result = await db.execute(
            text("SELECT * FROM b2c.get_platform_stats()")
        )
        stats = result.one_or_none()
        
        if stats:
            total_workspaces, personal_workspaces, team_workspaces, total_users = stats
        else:
            total_workspaces = personal_workspaces = team_workspaces = total_users = 0
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching B2C stats: {e}")
        
        # B2C schema doesn't exist or query failed - return zeros
        total_workspaces = 0
        personal_workspaces = 0
        team_workspaces = 0
        total_users = 0
    
    return B2CStats(
        total_workspaces=total_workspaces,
        personal_workspaces=personal_workspaces,
        team_workspaces=team_workspaces,
        total_users=total_users
    )


# --- Plan Management Endpoints ---

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """List all subscription plans (including archived)"""
    # Platform admin sees all plans
    stmt = select(SubscriptionPlan).order_by(
        SubscriptionPlan.tier_key, 
        desc(SubscriptionPlan.effective_from)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/plans", response_model=PlanResponse)
async def create_plan_version(
    plan: PlanCreate,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(verify_platform_admin)
):
    """Create a new version of a plan"""
    # Create new plan record
    new_plan = SubscriptionPlan(
        tier_key=plan.tier_key,
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        provider_config=plan.provider_config,
        limits=plan.limits,
        features=plan.features,
        effective_from=datetime.now(), # Effective immediately
        created_by=UUID(admin['uid']) if 'uid' in admin else None
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan


@router.post("/plans/{plan_id}/archive", response_model=PlanResponse)
async def archive_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Archive a plan version (soft delete)"""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    plan.archived_at = datetime.now()
    await db.commit()
    await db.refresh(plan)
    return plan

@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(verify_platform_admin)
):
    """Get specific plan details"""
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    return plan
