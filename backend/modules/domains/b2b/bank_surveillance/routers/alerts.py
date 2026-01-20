from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models.alert import AlertStatus, AlertSeverity, RiskType
from modules.domains.b2b.bank_surveillance.schemas.alert import AlertCreate, AlertUpdate, AlertFilter, AlertResponse
from modules.domains.b2b.bank_surveillance.services.alert_service import alert_service

router = APIRouter(prefix="/api/b2b/domain/bank_surveillance/alerts", tags=["Bank Surveillance Alerts"])

@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    risk_type: Optional[RiskType] = None,
    assigned_to: Optional[UUID] = None,
    communication_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """List risk alerts with filtering."""
    tenant_id = current_user["tenant_id"]
    
    filters = AlertFilter(
        status=status,
        severity=severity,
        risk_type=risk_type,
        assigned_to=assigned_to,
        communication_id=communication_id
    )
    
    alerts, total = await alert_service.list_alerts(db, tenant_id, filters, limit, offset)
    return alerts

@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "write")
):
    """Manually create an alert (mostly for testing/seeding)."""
    tenant_id = current_user["tenant_id"]
    
    # Enforce tenant_id matches token
    if alert_in.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create alert for other tenant")
        
    alert = await alert_service.create_alert(db, alert_in)
    await db.commit()
    return alert

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """Get alert details."""
    tenant_id = current_user["tenant_id"]
    
    alert = await alert_service.get_alert(db, alert_id, tenant_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_in: AlertUpdate,
    alert_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "update")
):
    """Update alert status, assignment, or details."""
    tenant_id = current_user["tenant_id"]
    
    alert = await alert_service.update_alert(db, alert_id, tenant_id, alert_in)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return alert

@router.post("/{alert_id}/escalate", response_model=AlertResponse)
async def escalate_alert(
    alert_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "update")
):
    """Quickly escalate an alert."""
    tenant_id = current_user["tenant_id"]
    
    alert = await alert_service.escalate_alert(db, alert_id, tenant_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return alert

@router.post("/{alert_id}/close", response_model=AlertResponse)
async def close_alert(
    alert_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "update")
):
    """Close an alert."""
    tenant_id = current_user["tenant_id"]
    
    alert = await alert_service.close_alert(db, alert_id, tenant_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return alert
