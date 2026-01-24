from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import uuid

from core.db.session import get_db
from modules.b2b.rbac import require_permission
from modules.domains.b2b.bank_surveillance.models.communication import Communication
from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
from modules.domains.b2b.bank_surveillance.schemas.communication import CommunicationResponse

router = APIRouter(prefix="", tags=["Communications"])

@router.get("/messages/{message_id}", response_model=CommunicationResponse)
async def get_message(
    message_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("communications", "read")
):
    """Get a specific message by ID."""
    tenant_id = current_user["tenant_id"]
    result = await db.execute(
        select(Communication)
        .where(Communication.id == message_id)
        .where(Communication.tenant_id == tenant_id)
    )
    comm = result.scalar_one_or_none()
    if not comm:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Phase 7: Storage Refactor - Content lives in ES
    if not comm.content and comm.message_id:
        # Ingestion uses 'message_id' as the ES Document ID
        content = await communication_rag_service.get_content_by_id(str(comm.message_id))
        if content:
            comm.content = content
            
    return comm

@router.get("/search")
async def search_communications(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("rag_search", "read")
):
    """Search communications using RAG (Hybrid/Vector)."""
    tenant_id = current_user["tenant_id"]
    results = await communication_rag_service.search(query=q, tenant_id=tenant_id, limit=limit)
    return results

@router.get("/communications", response_model=List[CommunicationResponse])
async def list_communications(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("communications", "read")
):
    """List recent communications."""
    tenant_id = current_user["tenant_id"]
    
    stmt = (
        select(Communication)
        .where(Communication.tenant_id == tenant_id)
        .order_by(Communication.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
