from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.schemas.regulatory import (
    RegulatoryDocumentCreate, 
    RegulatoryDocumentUpdate, 
    RegulatoryDocumentResponse
)
from modules.domains.b2b.bank_surveillance.services.regulatory_service import regulatory_service

router = APIRouter(prefix="/regulatory", tags=["Regulatory Library"])

@router.get("/", response_model=List[RegulatoryDocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("regulatory", "read")
):
    """List all regulatory documents for the current tenant."""
    tenant_id = current_user["tenant_id"]
    return await regulatory_service.list_documents(db, tenant_id, limit, offset)

@router.post("/", response_model=RegulatoryDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: RegulatoryDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("regulatory", "write")
):
    """Create a new regulatory document."""
    tenant_id = current_user["tenant_id"]
    if doc_in.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot create document for another tenant")
    
    doc = await regulatory_service.create_document(db, doc_in)
    await db.commit()
    return doc

@router.get("/{doc_id}", response_model=RegulatoryDocumentResponse)
async def get_document(
    doc_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("regulatory", "read")
):
    """Get a specific regulatory document by ID."""
    tenant_id = current_user["tenant_id"]
    doc = await regulatory_service.get_document(db, doc_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.patch("/{doc_id}", response_model=RegulatoryDocumentResponse)
async def update_document(
    doc_in: RegulatoryDocumentUpdate,
    doc_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("regulatory", "update")
):
    """Update an existing regulatory document."""
    tenant_id = current_user["tenant_id"]
    doc = await regulatory_service.update_document(db, doc_id, tenant_id, doc_in)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.commit()
    return doc

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("regulatory", "delete")
):
    """Delete a regulatory document."""
    tenant_id = current_user["tenant_id"]
    success = await regulatory_service.delete_document(db, doc_id, tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.commit()
