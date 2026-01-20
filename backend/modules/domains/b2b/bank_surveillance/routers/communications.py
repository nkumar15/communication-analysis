from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import uuid

from core.db.session import get_db
from modules.domains.b2b.bank_surveillance.models.communication import Communication
from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
from modules.domains.b2b.bank_surveillance.schemas.communication import CommunicationResponse

router = APIRouter(prefix="/api/b2b/domain/bank_surveillance", tags=["Communications"])

@router.get("/messages/{message_id}", response_model=CommunicationResponse)
async def get_message(message_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific message by ID."""
    result = await db.execute(select(Communication).where(Communication.id == message_id))
    comm = result.scalar_one_or_none()
    if not comm:
        raise HTTPException(status_code=404, detail="Message not found")
    return comm

@router.get("/search")
async def search_communications(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """Search communications using RAG (Hybrid/Vector)."""
    # For POC, use dummy ID. Real implementation uses Auth context.
    dummy_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, "unknown") 
    
    results = await communication_rag_service.search(query=q, tenant_id=dummy_tenant_id, limit=limit)
    return results

from modules.b2b.middleware.b2b_auth import get_current_active_user
from core.db.rls import rls_service
from infrastructure.logging import get_logger

logger = get_logger(__name__)

@router.get("/communications", response_model=List[CommunicationResponse])
async def list_communications(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List recent communications."""
    tenant_id = current_user["tenant_id"]
    # RLS context is already set by get_current_active_user, but we can ensure it here or rely on middleware.
    # To follow previous instruction strictness and defensive coding:
    await rls_service.set_tenant_context(db, tenant_id)
    
    stmt = select(Communication).where(Communication.tenant_id == tenant_id).order_by(Communication.timestamp.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()
