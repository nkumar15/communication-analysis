"""
Risk Events Router - API for viewing individual detection matches.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, date

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models import RiskEvent

router = APIRouter(prefix="/risk-events", tags=["Risk Events"])


class RiskEventResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    communication_id: UUID
    control_id: UUID
    sender: str
    event_date: date
    match_type: str
    matched_keywords: list
    matched_snippet: Optional[str]
    match_score: float
    incident_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RiskEventResponse])
async def list_risk_events(
    incident_id: Optional[UUID] = Query(None, description="Filter by incident"),
    control_id: Optional[UUID] = Query(None, description="Filter by control"),
    sender: Optional[str] = Query(None, description="Filter by sender"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """List risk events with optional filtering."""
    tenant_id = current_user["tenant_id"]
    
    stmt = select(RiskEvent).where(RiskEvent.tenant_id == tenant_id)
    
    if incident_id:
        stmt = stmt.where(RiskEvent.incident_id == incident_id)
    if control_id:
        stmt = stmt.where(RiskEvent.control_id == control_id)
    if sender:
        stmt = stmt.where(RiskEvent.sender.ilike(f"%{sender}%"))
    if start_date:
        stmt = stmt.where(RiskEvent.event_date >= start_date)
    if end_date:
        stmt = stmt.where(RiskEvent.event_date <= end_date)
    
    stmt = stmt.order_by(RiskEvent.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{event_id}", response_model=RiskEventResponse)
async def get_risk_event(
    event_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """Get a single risk event by ID."""
    tenant_id = current_user["tenant_id"]
    
    stmt = select(RiskEvent).where(
        RiskEvent.id == event_id,
        RiskEvent.tenant_id == tenant_id
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Risk event not found")
    
    return event
