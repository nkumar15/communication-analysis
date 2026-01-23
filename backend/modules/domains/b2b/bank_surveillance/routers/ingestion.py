"""
Ingestion API Router - Triggers and monitors daily dump ingestion jobs.
"""
from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models.ingestion_log import IngestionLog
from modules.domains.b2b.bank_surveillance.tasks.ingestion import ingest_daily_dump

router = APIRouter(
    prefix="/ingestion", 
    tags=["Ingestion"]
)


class TriggerRequest(BaseModel):
    date: str  # YYYYMMDD
    file_path: Optional[str] = None
    force: bool = False


class TriggerResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    date: str
    status: str
    file_path: str
    processed_count: int
    error_count: int
    started_at: datetime
    completed_at: Optional[datetime]


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_ingestion(
    request: TriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("ingestion", "write")
):
    """
    Manually trigger ingestion for a specific date's dump file.
    """
    # Default file path pattern if not provided
    file_path = request.file_path or f"/data/dumps/{request.date}.csv"
    
    # Check if already ingested (unless force=True)
    if not request.force:
        stmt = select(IngestionLog).where(
            IngestionLog.date == request.date,
            IngestionLog.status == "completed"
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Date {request.date} already ingested. Use force=true to re-ingest."
            )
    
    # Dispatch Celery task
    import celery
    print(f"DEBUG: Celery Broker URL: {celery.current_app.conf.broker_url}", flush=True)
    
    try:
        task = ingest_daily_dump.delay(file_path, request.date)
        print(f"DEBUG: Task dispatched. ID: {task.id}", flush=True)
    except Exception as e:
        print(f"DEBUG: Task dispatch FAILED: {e}", flush=True)
        raise e
    
    return TriggerResponse(
        job_id=task.id,
        status="queued",
        message=f"Ingestion job queued for {request.date}"
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("ingestion", "read")
):
    """
    Get status of an ingestion job.
    """
    stmt = select(IngestionLog).where(IngestionLog.job_id == UUID(job_id))
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return JobStatusResponse(
        job_id=str(log.job_id),
        date=log.date,
        status=log.status,
        file_path=log.file_path,
        processed_count=log.processed_count,
        error_count=log.error_count,
        started_at=log.started_at,
        completed_at=log.completed_at
    )


@router.post("/retry/{job_id}", response_model=TriggerResponse)
async def retry_ingestion(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("ingestion", "write")
):
    """
    Retry a failed ingestion job.
    """
    stmt = select(IngestionLog).where(IngestionLog.job_id == UUID(job_id))
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if log.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not in failed state (current: {log.status})"
        )
    
    # Re-dispatch
    task = ingest_daily_dump.delay(log.file_path, log.date)
    
    return TriggerResponse(
        job_id=task.id,
        status="queued",
        message=f"Retry job queued for {log.date}"
    )


from typing import List
from sqlalchemy import func, desc


class IngestionStatsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    total_messages: int
    today_messages: int


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("ingestion", "read")
):
    """
    List recent ingestion jobs.
    """
    stmt = select(IngestionLog).order_by(desc(IngestionLog.started_at)).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    return [
        JobStatusResponse(
            job_id=str(log.job_id),
            date=log.date,
            status=log.status,
            file_path=log.file_path,
            processed_count=log.processed_count,
            error_count=log.error_count,
            started_at=log.started_at,
            completed_at=log.completed_at
        )
        for log in logs
    ]


@router.get("/stats", response_model=IngestionStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("ingestion", "read")
):
    """
    Get ingestion statistics for dashboard.
    """
    from datetime import date
    today = date.today().strftime("%Y%m%d")
    
    # Count jobs by status
    total = await db.execute(select(func.count(IngestionLog.job_id)))
    completed = await db.execute(
        select(func.count(IngestionLog.job_id)).where(IngestionLog.status == "completed")
    )
    failed = await db.execute(
        select(func.count(IngestionLog.job_id)).where(IngestionLog.status == "failed")
    )
    running = await db.execute(
        select(func.count(IngestionLog.job_id)).where(IngestionLog.status == "running")
    )
    
    # Sum processed counts
    total_msgs = await db.execute(
        select(func.coalesce(func.sum(IngestionLog.processed_count), 0))
    )
    today_msgs = await db.execute(
        select(func.coalesce(func.sum(IngestionLog.processed_count), 0)).where(
            IngestionLog.date == today
        )
    )
    
    return IngestionStatsResponse(
        total_jobs=total.scalar() or 0,
        completed_jobs=completed.scalar() or 0,
        failed_jobs=failed.scalar() or 0,
        running_jobs=running.scalar() or 0,
        total_messages=total_msgs.scalar() or 0,
        today_messages=today_msgs.scalar() or 0
    )

