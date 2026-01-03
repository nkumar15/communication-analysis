from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from backend.core.db.session import get_db
from backend.modules.domains.enron.models import EnronEmail
from backend.modules.domains.enron.schemas import EnronEmailResponse
from backend.modules.domains.enron.services.rag import enron_rag_service

router = APIRouter(prefix="/enron", tags=["Enron"])

@router.get("/emails/{email_id}", response_model=EnronEmailResponse)
async def get_email(email_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific email by ID."""
    result = await db.execute(select(EnronEmail).where(EnronEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email

@router.get("/search")
async def search_emails(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """Search emails using RAG (Hybrid/Vector)."""
    # For POC, we use a default tenant_id derived from a fixed string as described in ingestion
    # Ideally, this comes from auth context.
    # We'll use a placeholder tenant for search across all 'enron' data for now.
    # Ingestion used uuid5(NAMESPACE_DNS, username).
    # If we want to search ALL, we might need a way to search across tenants or use a 'master' tenant.
    # For now, let's assume we search a specific known desk/tenant or just use a dummy one if RAG service handles it.
    # EnronRagService.search implementation had TODO for filter.
    # We will pass a dummy UUID for now.
    dummy_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, "unknown") 
    
    results = await enron_rag_service.search(query=q, tenant_id=dummy_tenant_id, limit=limit)
    return results
