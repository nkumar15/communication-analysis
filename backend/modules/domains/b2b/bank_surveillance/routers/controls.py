from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.schemas.control import (
    SurveillanceControlCreate, 
    SurveillanceControlUpdate, 
    SurveillanceControlResponse
)
from modules.domains.b2b.bank_surveillance.services.control_service import control_service

router = APIRouter(prefix="/controls", tags=["Surveillance Controls"])

@router.get("/", response_model=List[SurveillanceControlResponse])
async def list_controls(
    risk_typology: Optional[str] = Query(None),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("controls", "read")
):
    """List all surveillance controls for the current tenant."""
    tenant_id = current_user["tenant_id"]
    scopes = current_user.get("geographic_scopes")
    return await control_service.list_controls(db, tenant_id, risk_typology, limit, offset, access_scopes=scopes)

@router.post("/", response_model=SurveillanceControlResponse, status_code=status.HTTP_201_CREATED)
async def create_control(
    control_in: SurveillanceControlCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("controls", "write")
):
    """Create a new surveillance control."""
    tenant_id = current_user["tenant_id"]
    if control_in.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create control for another tenant")
    
    control = await control_service.create_control(db, control_in)
    await db.commit()
    return control

@router.get("/{control_id}", response_model=SurveillanceControlResponse)
async def get_control(
    control_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("controls", "read")
):
    """Get a specific surveillance control by ID."""
    tenant_id = current_user["tenant_id"]
    scopes = current_user.get("geographic_scopes")
    control = await control_service.get_control(db, control_id, tenant_id, access_scopes=scopes)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return control

@router.patch("/{control_id}", response_model=SurveillanceControlResponse)
async def update_control(
    control_in: SurveillanceControlUpdate,
    control_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("controls", "update")
):
    """Update an existing surveillance control."""
    tenant_id = current_user["tenant_id"]
    scopes = current_user.get("geographic_scopes")
    control = await control_service.update_control(db, control_id, tenant_id, control_in, access_scopes=scopes)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    await db.commit()
    return control

@router.delete("/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_control(
    control_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("controls", "delete")
):
    """Delete a surveillance control."""
    tenant_id = current_user["tenant_id"]
    scopes = current_user.get("geographic_scopes")
    success = await control_service.delete_control(db, control_id, tenant_id, access_scopes=scopes)
    if not success:
        raise HTTPException(status_code=404, detail="Control not found")
    await db.commit()
