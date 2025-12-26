
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

# Generic Celery instance for producing tasks
from celery import Celery
celery_producer = Celery('api_producer', broker=settings.celery_broker_url_resolved)

router = APIRouter(
    prefix="/api/domain/rag",
    tags=["RAG"],
    responses={404: {"description": "Not found"}},
)

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    company_name: Optional[str] = Form(None),
    report_type: Optional[str] = Form(None),
    financial_period: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    # RLS/Auth dependencies would go here (e.g. current_user or tenant_id from context)
    # Asking for tenant_id in Form for simplicity in Phase 2 if auth isn't fully mocked yet
    # But usually we extract from token. Assuming tenant_id is available in RLS/Context.
    # For now, let's inject tenant_id via Form or Headers for dev testing if needed,
    # or rely on `rls_service.get_current_tenant_id` if auth middleware ran.
    # We'll use a specific Form field for dev purpose as auth provider might be mocked.
    tenant_id: str = Form(...) 
):
    """
    Upload a document for RAG ingestion.
    1. Hashing
    2. MinIO Upload
    3. DB Record (Pending)
    4. Async Task
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")
    
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
            "source": file.filename
        }
    }
    
    celery_producer.send_task("domain.ingest_document", args=[payload])
    
    return {
        "status": "pending",
        "job_id": job_id,
        "document_id": str(new_doc.id),
        "message": "Upload successful, ingestion started."
    }

@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str, 
    tenant_id: str, # Required for RLS
    db: AsyncSession = Depends(get_db)
):
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
    query: str = Form(...),
    tenant_id: str = Form(...),
    limit: int = Form(5),
    db: AsyncSession = Depends(get_db)
):
    """
    Search ingested documents.
    NOTE: This endpoint requires 'llama-index' and embedding models, which might
    not be present in the lightweight 'domain-api' container.
    """
    try:
        from infrastructure.factories.vector_store_factory import VectorStoreFactory
        from infrastructure.factories.embedding_factory import EmbeddingFactory
        from llama_index.core import Settings
        from modules.domains.nse.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever
    except ImportError:
         raise HTTPException(
             status_code=501, 
             detail="Search functionality requires 'llama-index' libraries which are not installed in the API container. Please use the worker for retrieval or configure a remote API-based embedding provider."
         )

    try:
        # 1. Initialize Components (Lazy load)
        embed_model = EmbeddingFactory.get_embedding_model()
        # vector_store not needed for HybridRetriever as it uses direct ES client, 
        # but factory usage ensures env vars are checked if we wanted to use standard store.
        # HybridRetriever initializes its own AsyncElasticsearch client based on env.
        
        # 2. Setup Settings (Optional but good practice)
        Settings.embed_model = embed_model
        
        # 3. Create Custom Retriever (Tenant-Aware Hybrid RRF)
        retriever = TenantAwareHybridRetriever(
            embed_model=embed_model,
            tenant_id=str(tenant_id),
            top_k=limit
        )
        
        # 4. Execute Search (Async)
        results = await retriever.aretrieve(query)
        
        # 5. Format Response
        response = []
        for node in results:
            response.append({
                "text": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
            
        return {"results": response}
    except Exception as e:
        # Log the full error
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
