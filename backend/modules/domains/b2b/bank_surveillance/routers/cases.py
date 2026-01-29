from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from core.db.session import get_db
from modules.b2b.middleware import get_current_active_user
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.services.case_service import case_service
from modules.domains.b2b.bank_surveillance.schemas.case import (
    CaseCreate, CaseUpdate, CaseResponse, CaseListResponse,
    CaseNoteCreate, CaseNoteResponse,
    CaseEvidenceCreate, CaseEvidenceResponse,
    CaseStats
)

router = APIRouter(prefix="/cases", tags=["Surveillance Case Management"])

@router.get("/stats", response_model=CaseStats)
async def get_case_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "read")
):
    """Get summary statistics for cases."""
    tenant_id = current_user['tenant_id']
    scopes = current_user.get("geographic_scopes")
    return await case_service.get_case_stats(db, tenant_id=tenant_id, access_scopes=scopes)


@router.post("/", response_model=CaseListResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    obj_in: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "write")
):
    """Create a new compliance case."""
    return await case_service.create_case(db, obj_in, tenant_id=current_user['tenant_id'])


@router.get("/", response_model=List[CaseListResponse])
async def list_cases(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "read")
):
    """List all cases for the current tenant."""
    tenant_id = current_user['tenant_id']
    scopes = current_user.get("geographic_scopes")
    return await case_service.list_cases(db, tenant_id=tenant_id, status=status, limit=limit, offset=offset, access_scopes=scopes)

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "read")
):
    """Fetch details for a specific case."""
    tenant_id = current_user["tenant_id"]
    db_obj = await case_service.get_case(db, case_id, tenant_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_obj

@router.patch("/{case_id}", response_model=CaseListResponse)
async def update_case(
    case_id: uuid.UUID,
    obj_in: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "update")
):
    """Update case status, assignment, or metadata."""
    tenant_id = current_user["tenant_id"]
    
    # Validation: Closure requires rationale
    if obj_in.status == "closed" and not obj_in.decision_rationale:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Decision rationale is mandatory when closing a case."
        )
        
    db_obj = await case_service.update_case(db, case_id, tenant_id, obj_in)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_obj

@router.post("/{case_id}/notes", response_model=CaseNoteResponse)
async def add_case_note(
    case_id: uuid.UUID,
    obj_in: CaseNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "update")
):
    """Add an internal note to a case."""
    return await case_service.add_note(db, case_id, obj_in, author_id=current_user['id'])

@router.post("/{case_id}/evidence", response_model=CaseEvidenceResponse)
async def add_case_evidence(
    case_id: uuid.UUID,
    obj_in: CaseEvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("cases", "update")
):
    """Link evidence (communication or alert) to a case."""
    return await case_service.add_evidence(db, case_id, obj_in)
