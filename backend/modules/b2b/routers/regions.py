from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from core.db.session import get_db
from core.db.rls import rls_service
from modules.b2b.middleware import get_current_active_user
from modules.b2b.models.geographic_region import GeographicRegion
from pydantic import BaseModel

router = APIRouter(prefix="/api/b2b/regions", tags=["regions"])

class RegionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    class Config:
        from_attributes = True

@router.get("/", response_model=List[RegionResponse])
async def list_regions(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all geographic regions for the current tenant (RLS Enabled)"""
    
    # 1. Set RLS Context
    await rls_service.set_tenant_context(db, current_user['tenant_id'])
    
    # 2. Fetch Regions (No explicit tenant filtering needed due to RLS)
    stmt = select(GeographicRegion).order_by(GeographicRegion.code)
    
    result = await db.execute(stmt)
    regions = result.scalars().all()
    
    return regions
