
import hashlib
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db.session import get_db
from core.db.rls import rls_service
from core.config import settings
from infrastructure.factories.storage_factory import StorageFactory
from modules.b2b.models.rag_document import RagDocument
from modules.b2b.models.tenant import TenantModel
from modules.b2b.middleware.b2b_auth import get_current_active_user

from celery import Celery
celery_producer = Celery('api_producer', broker=settings.celery_broker_url_resolved)

# Import RagService at top level to ensure preloading of Reranker model on startup
from modules.domains.nse.services.rag_service import rag_service

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
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
    # ... (rest of code)

    # 4. Dispatch Task

    
    # Set RLS Context manually (since we bypass typical auth middleware for this testing endpoint)
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        await rls_service.set_tenant_context(db, tenant_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant_id format")
    
    # 1. Read & Hash
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()
    file_size = len(content)
    
    # Reset file cursor for upload (or pass bytes)
    # MinIO put_object needs stream or bytes
    # But we need to be careful with memory for large files. 
    # For < 50MB it's fine.
    
    import io
    file_stream = io.BytesIO(content)
    
    # 2. Upload to MinIO
    storage = StorageFactory.get_storage_client()
    bucket = "rag-documents"
    
    # Ensure bucket exists
    if not storage.bucket_exists(bucket):
        storage.make_bucket(bucket)
        
    object_name = f"{tenant_id}/{content_hash}/{file.filename}"
    
    storage.put_object(
        bucket,
        object_name,
        file_stream,
        length=file_size,
        content_type=file.content_type
    )
    
    s3_path = f"s3://{bucket}/{object_name}"
    
    # 3. DB Record
    # Check duplicates/upsert?
    # Phase 2 plan says: "If exists... delete old vectors -> Re-ingest".
    # For simplicity, we create a new RagDocument record for every upload job, 
    # but the Worker checks logic. OR we link here.
    # Let's create a NEW job/record every time to track history.
    
    job_id = str(uuid.uuid4())
    
    new_doc = RagDocument(
        tenant_id=uuid.UUID(tenant_id),
        filename=file.filename,
        file_url=s3_path,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        company_name=company_name,
        report_type=report_type,
        financial_period=financial_period,
        status="pending",
        content_hash=content_hash,
        job_id=job_id
    )
    
    db.add(new_doc)
    await db.commit()
    # await db.refresh(new_doc) - Removed: RLS context is lost after commit (SET LOCAL), 
    # and INSERT RETURNING already populates necessary fields (id, created_at).
    
    # 4. Dispatch Task
    payload = {
        "tenant_id": str(tenant_id),
        "file_path": s3_path,
        "job_id": job_id,
        "content_hash": content_hash,
        "document_metadata": {
            "company_name": company_name,
            "report_type": report_type,
            "financial_period": financial_period,
            "source": file.filename,
            "original_filename": file.filename,
            "content_hash": content_hash
        }
    }
    
    celery_producer.send_task("domain.ingest_document", args=[payload], queue="domain")
    
    return {
        "status": "pending",
        "job_id": job_id,
        "document_id": str(new_doc.id),
        "message": "Upload successful, ingestion started."
    }

@router.get("/status/{job_id}")
async def get_ingestion_status(
    domain: str,
    job_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """Check status of an ingestion job"""
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        await rls_service.set_tenant_context(db, tenant_uuid)
    except ValueError:
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
    limit: int = Form(5),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """
    Search ingested documents using the centralized RagService.
    This ensures Query Understanding (Decomposition) and advanced retrieval logic is applied.
    """
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
        
        # The frontend likely expects 'answer' and 'results'.
        # rag_service.search calculates results. 
        # Currently rag_service.search doesn't synthesized "answer" in the version I viewed?
        # WAIT: I need to check if rag_service has synthesis. 
        # The `rag_service.py` I viewed earlier had "Synthesize (TODO)". 
        # But this router HAD synthesis. Eek.
        # I must migrate synthesis logic to rag_service OR keep it here for now but use the results from rag_service for retrieval.
        
        # To strictly fix the filtering issue, I will user rag_service to get NODES/RESULTS, 
        # then keep the simple synthesis here if needed, OR better: move synthesis to rag_service.
        
        # Let's check `rag_service.py` again. It did NOT have synthesis implemented (lines 84 "Synthesize (TODO)").
        # The Router DID have synthesis (Lines 278-307).
        
        # STRATEGY: 
        # 1. Use rag_service.search to get filtered results.
        # 2. Re-implement the synthesis block here using those results to maintain feature parity (Q&A).
        
        results = search_result.get("results", [])
        filters_used = search_result.get("filters", [])
        
        # 7. Generate Answer (Synthesize) - Preserving existing Router logic
        answer = "I could not find enough relevant information to answer your question."
        if results:
            try:
                from infrastructure.factories.llm_factory import LLMFactory
                llm = LLMFactory.get_llm() 
                
                # Enrich context with metadata (Year/Quarter)
                context_str = "\n\n".join([
                    f"Source: {r.get('metadata', {}).get('source', 'Unknown')} "
                    f"({r.get('metadata', {}).get('fiscal_year', 'N/A')} {r.get('metadata', {}).get('quarter', '')})\n"
                    f"Content: {r.get('text', '')}"
                    for r in results
                ])
                
                prompt = (
                    "You are an expert financial analyst. Your goal is to answer the user's question comprehensively using the provided context.\n\n"
                    "**Guidelines:**\n"
                    "1. **Format**: Use **Markdown** (bolding for key figures, lists for points).\n"
                    "2. **Tables**: If the data allows, present financial figures in a Markdown table.\n"
                    "3. **Structure**: Organize your answer with clear headers (e.g., '### Executive Summary', '### Key Figures').\n"
                    "4. **Accuracy**: Use ONLY the provided context. If the exact answer isn't there, state what IS known relative to the topic.\n"
                    "5. **Citations**: Mention the Fiscal Year/Quarter if available in the source info.\n\n"
                    f"**Context**:\n{context_str}\n\n"
                    f"**Question**: {query}\n\n"
                    "**Answer**:"
                )
                
                response_gen = await llm.acomplete(prompt)
                answer = response_gen.text
            except Exception as e:
                print(f"Generation failed: {e}")
                answer = "Error generating answer."

        return {
            "answer": answer,
            "results": results,
            "filters": filters_used,
            "count": len(results)
        }

    except Exception as e:
        # Log the full error
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents(
    domain: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_active_user)
):
    tenant_id = str(current_user.get('tenant_id'))
    """List all RAG documents for a tenant"""
    try:
        tenant_uuid = uuid.UUID(tenant_id)
        # Verify tenant access (simple check or RLS context)
        await rls_service.set_tenant_context(db, tenant_uuid)
    except ValueError:
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
            "job_id": d.job_id
        }
        for d in docs
    ]
