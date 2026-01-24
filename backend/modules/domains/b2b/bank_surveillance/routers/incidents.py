"""
Incidents Router - API for viewing aggregated risk incidents.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, date

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models import Incident, RiskEvent

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    control_id: UUID
    sender: str
    incident_date: date
    event_count: int
    severity: str
    status: str
    alert_id: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class IncidentDetailResponse(IncidentResponse):
    events: List[dict] = []


@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    alert_id: Optional[UUID] = Query(None, description="Filter by alert"),
    control_id: Optional[UUID] = Query(None, description="Filter by control"),
    sender: Optional[str] = Query(None, description="Filter by sender"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """List incidents with optional filtering."""
    tenant_id = current_user["tenant_id"]
    
    stmt = select(Incident).where(Incident.tenant_id == tenant_id)
    
    if alert_id:
        stmt = stmt.where(Incident.alert_id == alert_id)
    if control_id:
        stmt = stmt.where(Incident.control_id == control_id)
    if sender:
        stmt = stmt.where(Incident.sender.ilike(f"%{sender}%"))
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)
    if start_date:
        stmt = stmt.where(Incident.incident_date >= start_date)
    if end_date:
        stmt = stmt.where(Incident.incident_date <= end_date)
    
    stmt = stmt.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """Get incident details with linked risk events."""
    tenant_id = current_user["tenant_id"]
    
    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.tenant_id == tenant_id
    ).options(selectinload(Incident.events))
    
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Build response with events
    events_data = [
        {
            "id": str(e.id),
            "communication_id": str(e.communication_id),
            "match_type": e.match_type,
            "matched_keywords": e.matched_keywords,
            "matched_snippet": e.matched_snippet,
            "match_score": e.match_score,
        }
        for e in incident.events
    ]
    
    return IncidentDetailResponse(
        id=incident.id,
        tenant_id=incident.tenant_id,
        control_id=incident.control_id,
        sender=incident.sender,
        incident_date=incident.incident_date,
        event_count=incident.event_count,
        severity=incident.severity,
        status=incident.status,
        alert_id=incident.alert_id,
        created_at=incident.created_at,
        events=events_data
    )
