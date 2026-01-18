
import hashlib
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db.session import get_db
from core.db.rls import rls_service
from core.config import settings
from core.constants import DocumentStatus, RAGDefaults
from infrastructure.logging import get_logger, add_context
from modules.b2b.models.rag_document import RagDocument
from modules.b2b.middleware.b2b_auth import get_current_active_user

# Import services
from modules.domains.b2c.finance_trader.services.document_service import document_service
from modules.domains.b2c.finance_trader.services.synthesis_service import synthesis_service
from modules.domains.b2c.finance_trader.services.rag_service import rag_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/domain/{domain}/rag",
    tags=["RAG"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload")
async def upload_document(
    domain: str,
    file: UploadFile = File(...),
    company_name: Optional[str] = Form(None),
    report_type: Optional[str] = Form(None),
    financial_period: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """
    Upload a document for RAG ingestion.
    """
    # Bind context for all logs in this request
    add_context(tenant_id=tenant_id, domain=domain, filename=file.filename or "unknown")
    
    if not file.filename:
        logger.warning("upload_rejected_no_filename", tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail="Filename missing")
    
    logger.info("document_upload_started", file_size=file.size)
    
    # Use DocumentService for all upload logic
    try:
        tenant_uuid = uuid.UUID(tenant_id)
    except ValueError:
        logger.error("invalid_tenant_id_format", tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    
    metadata = {
        "company_name": company_name,
        "report_type": report_type,
        "financial_period": financial_period,
        "original_filename": file.filename
    }
    
    result = await document_service.upload_document(
        db=db,
        tenant_id=tenant_uuid,
        file=file,
        metadata=metadata
    )
    
    return result.to_dict()

@router.get("/status/{job_id}")
async def get_ingestion_status(
    domain: str,
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """Check status of an ingestion job"""
    add_context(tenant_id=tenant_id, domain=domain, job_id=job_id)
    
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        await rls_service.set_tenant_context(db, tenant_uuid)
    except ValueError:
        logger.error("invalid_tenant_id_format", tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")

    stmt = select(RagDocument).where(RagDocument.job_id == job_id)
    result = await db.execute(stmt)
    doc = result.scalars().first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": doc.job_id,
        "status": doc.status,
        "error_message": doc.error_message,
        "chunks": doc.chunk_count,
        "created_at": doc.created_at
    }

@router.post("/search")
async def search_documents(
    domain: str,
    query: str = Form(...),
    limit: int = Form(3, ge=1), # Reduced default from 5 to 3 for performance
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """
    Search ingested documents using the centralized RagService.
    This ensures Query Understanding (Decomposition) and advanced retrieval logic is applied.
    """
    add_context(tenant_id=tenant_id, domain=domain, query=query[:50])
    try:
        # rag_service is imported at module level for preloading
        
        # Call the service which handles:
        # 1. Query Decomposition (NL -> Filters)
        # 2. Hybrid Retrieval with Tenant Isolation
        # 3. Reranking (if configured)
        # 4. Synthesis (if configured, currently partial)
        
        # Note: rag_service.search returns a dict with 'results', 'filters', etc.
        # We might need to adapt the response specific to what the frontend expects 
        # or just return the service response.
        
        # The service returns:
        # {
        #     "query": query,
        #     "filters": [...],
        #     "results": [...],
        #     "count": ...
        # }
        
        search_result = await rag_service.search(query=query, tenant_id=uuid.UUID(tenant_id), limit=limit)
        
        results = search_result.get("results", [])
        filters_used = search_result.get("filters", [])
        
        # Generate answer using SynthesisService
        answer = await synthesis_service.synthesize_answer(
            query=query,
            results=results,
            domain=domain
        )

        return {
            "query": query,
            "answer": answer,
            "results": results,
            "context": results,  # Alias for compatibility with tests/frontend
            "filters": filters_used,
            "count": len(results)
        }

    except Exception as e:
        logger.error("search_failed", query=query, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Search operation failed")

@router.get("/documents")
async def list_documents(
    domain: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """List all RAG documents for a tenant"""
    add_context(tenant_id=tenant_id, domain=domain)
    
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        await rls_service.set_tenant_context(db, tenant_uuid)
    except ValueError:
        logger.error("invalid_tenant_id_format", tenant_id=tenant_id)
        raise HTTPException(status_code=400, detail="Invalid tenant_id")

    stmt = select(RagDocument).where(RagDocument.tenant_id == tenant_uuid).order_by(RagDocument.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "created_at": d.created_at,
            "file_size_bytes": d.file_size_bytes,
            "file_size_bytes": d.file_size_bytes,
            "job_id": d.job_id,
            "company_name": d.company_name,
            "report_type": d.report_type,
            "financial_period": d.financial_period
        }
        for d in docs
    ]
