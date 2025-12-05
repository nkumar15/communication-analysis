from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional, List
from datetime import datetime
import csv
import io

from core.database import get_db
from services.b2b.middleware.b2b_auth import require_role
from services.b2b.models.audit_log import AuditLog
from services.b2b.schemas.audit_logs import AuditLogList, AuditLogResponse

router = APIRouter(prefix="/api/b2b/audit-logs", tags=["audit-logs"])

@router.get("", response_model=AuditLogList)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(require_role(["owner", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """
    List audit logs for the tenant.
    Restricted to Owner and Admin roles.
    """
    tenant_id = current_user["tenant_id"]
    offset = (page - 1) * limit

    # Base query
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    # Filters
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Fetch items
    query = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit
    }

@router.get("/export")
async def export_audit_logs(
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(require_role(["owner", "admin"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Export audit logs as CSV.
    Restricted to Owner and Admin roles.
    """
    tenant_id = current_user["tenant_id"]

    # Base query
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    # Filters
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)

    query = query.order_by(desc(AuditLog.created_at))

    async def iter_csv():
        # CSV Header
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Event Type", "Actor ID", "Resource Type", "Resource ID", "IP Address", "User Agent", "Details"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # Stream rows
        result = await db.stream(query)
        async for row in result:
            log = row[0]
            writer.writerow([
                log.created_at.isoformat(),
                log.event_type,
                str(log.actor_id) if log.actor_id else "",
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                log.ip_address or "",
                log.user_agent or "",
                str(log.details)
            ])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
