
import hashlib
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db.session import get_db
from core.db.rls import rls_service
from core.config import settings
from core.constants import DocumentStatus, RAGDefaults
from infrastructure.logging import get_logger, add_context
# USE B2C MODEL
from modules.domains.b2c.finance_trader.models.rag_document import RagDocument
# USE B2C AUTH
from modules.b2c.middleware.b2c_auth import get_current_b2c_user

# Import services
from modules.domains.b2c.finance_trader.services.document_service import document_service
from modules.domains.b2c.finance_trader.services.synthesis_service import synthesis_service
from modules.domains.b2c.finance_trader.services.rag_service import rag_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
    responses={404: {"description": "Not found"}},
)

async def get_workspace_context(
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    current_user: dict = Depends(get_current_b2c_user)
) -> uuid.UUID:
    """
    Resolve and validate workspace context.
    Prioritize X-Workspace-ID header, fallback to user's personal workspace.
    """
    workspace_id_str = x_workspace_id or str(current_user.get("personal_workspace_id"))
    
    if not workspace_id_str:
        # Should not happen if user is valid B2C user
        raise HTTPException(status_code=400, detail="No active workspace context")
        
    try:
        workspace_id = uuid.UUID(workspace_id_str)
        # TODO: Validate user membership in this workspace if not personal
        return workspace_id
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    company_name: Optional[str] = Form(None),
    report_type: Optional[str] = Form(None),
    financial_period: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_b2c_user),
    workspace_id: uuid.UUID = Depends(get_workspace_context)
):
    """
    Upload a document for RAG ingestion.
    """
    domain = "finance_trader"
    """
    Upload a document for RAG ingestion.
    """
    # Bind context for all logs in this request
    add_context(workspace_id=str(workspace_id), user_id=str(current_user['id']), domain=domain, filename=file.filename or "unknown")
    
    if not file.filename:
        logger.warning("upload_rejected_no_filename", workspace_id=str(workspace_id))
        raise HTTPException(status_code=400, detail="Filename missing")
    
    logger.info("document_upload_started", file_size=file.size)
    
    metadata = {
        "company_name": company_name,
        "report_type": report_type,
        "financial_period": financial_period,
        "original_filename": file.filename
    }
    
    result = await document_service.upload_document(
        db=db,
        workspace_id=workspace_id,
        file=file,
        metadata=metadata,
        uploaded_by=current_user['id']
    )
    
    return result.to_dict()

@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_b2c_user), # Auth check
    workspace_id: uuid.UUID = Depends(get_workspace_context)
):
    """Check status of an ingestion job"""
    domain = "finance_trader"
    """Check status of an ingestion job"""
    add_context(workspace_id=str(workspace_id), domain=domain, job_id=job_id)

    # Validate ownership/workspace context via query
    stmt = select(RagDocument).where(
        RagDocument.job_id == job_id,
        RagDocument.workspace_id == workspace_id
    )
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
    query: str = Form(...),
    limit: int = Form(3, ge=1), # Reduced default from 5 to 3 for performance
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_b2c_user),
    workspace_id: uuid.UUID = Depends(get_workspace_context)
):
    """
    Search ingested documents using the centralized RagService.
    This ensures Query Understanding (Decomposition) and advanced retrieval logic is applied.
    """
    domain = "finance_trader"
    """
    Search ingested documents using the centralized RagService.
    This ensures Query Understanding (Decomposition) and advanced retrieval logic is applied.
    """
    add_context(workspace_id=str(workspace_id), domain=domain, query=query[:50])
    try:
        # Call the service
        # rag_service.search uses tenant_id arg for isolation, we pass workspace_id
        search_result = await rag_service.search(query=query, tenant_id=workspace_id, limit=limit)
        
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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_b2c_user),
    workspace_id: uuid.UUID = Depends(get_workspace_context)
):
    """List all RAG documents for a workspace"""
    domain = "finance_trader"
    """List all RAG documents for a workspace"""
    add_context(workspace_id=str(workspace_id), domain=domain)

    stmt = select(RagDocument).where(RagDocument.workspace_id == workspace_id).order_by(RagDocument.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "created_at": d.created_at,
            "file_size_bytes": d.file_size_bytes,
            "job_id": d.job_id,
            "company_name": d.company_name,
            "report_type": d.report_type,
            "financial_period": d.financial_period
        }
        for d in docs
    ]
