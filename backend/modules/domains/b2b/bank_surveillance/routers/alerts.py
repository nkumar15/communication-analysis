from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models.alert import AlertStatus, AlertSeverity, RiskType
from modules.domains.b2b.bank_surveillance.schemas.alert import AlertCreate, AlertUpdate, AlertFilter, AlertResponse, AlertStats
from modules.domains.b2b.bank_surveillance.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["Bank Surveillance Alerts"])

async def require_alert_update(
    current_user: dict = require_permission("alerts", "read"),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Dependency to allow either 'update' or 'acknowledge' permission."""
    from modules.b2b.rbac.permission_checker import has_permission_with_plugins
    user_id = current_user["id"]
    
    # Check for update OR acknowledge
    can_update = await has_permission_with_plugins(user_id, "alerts", "update", db, role_id=current_user.get("role_id"))
    can_acknowledge = await has_permission_with_plugins(user_id, "alerts", "acknowledge", db, role_id=current_user.get("role_id"))
    
    if not (can_update or can_acknowledge):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: alerts:update or alerts:acknowledge required"
        )
    return current_user


class GenerateAlertsRequest(BaseModel):
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD


class GenerateAlertsResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None


@router.post("/generate", response_model=GenerateAlertsResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_alerts(
    request: GenerateAlertsRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = require_permission("alerts", "write")
):
    """
    Trigger Workflow B: Aggregate RiskEvents into Incidents and generate Alerts.
    Processing happens asynchronously via Celery worker.
    """
    from modules.domains.b2b.bank_surveillance.tasks.alerting import generate_alerts as generate_alerts_task
    import uuid
    
    tenant_id = str(current_user["tenant_id"])
    job_id = str(uuid.uuid4())
    
    # Trigger Celery task
    generate_alerts_task.delay(tenant_id, request.start_date, request.end_date)
    
    return GenerateAlertsResponse(
        status="queued",
        message="Alert generation task queued",
        job_id=job_id
    )


@router.get("/stats", response_model=AlertStats)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("alerts", "read")
):
    """Get summary statistics for the Alerts Dashboard."""
    tenant_id = current_user["tenant_id"]
    return await alert_service.get_alert_stats(db, tenant_id)


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    risk_type: Optional[RiskType] = None,
    assigned_to: Optional[UUID] = None,
    communication_id: Optional[UUID] = None,
    region: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_desc: bool = True,
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
        communication_id=communication_id,
        region=region
    )
    
    alerts, total = await alert_service.list_alerts(db, tenant_id, filters, limit, offset, sort_by, sort_desc)
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
    current_user: dict = Depends(require_alert_update)
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
    current_user: dict = Depends(require_alert_update)
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
    current_user: dict = Depends(require_alert_update)
):
    """Close an alert."""
    tenant_id = current_user["tenant_id"]
    
    alert = await alert_service.close_alert(db, alert_id, tenant_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.commit()
    return alert
