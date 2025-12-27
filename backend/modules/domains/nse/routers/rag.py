
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

# Generic Celery instance for producing tasks
from celery import Celery
celery_producer = Celery('api_producer', broker=settings.celery_broker_url_resolved)

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
        # Fetch more candidates for reranking (e.g. 4x limit)
        initial_top_k = limit * 4
        retriever = TenantAwareHybridRetriever(
            embed_model=embed_model,
            tenant_id=str(tenant_id),
            top_k=initial_top_k
        )
        
        # 4. Execute Search (Async)
        nodes = await retriever.aretrieve(query)
        
        # 5. Rerank (Optional / if available)
        try:
            from infrastructure.factories.reranker_factory import RerankerFactory
            
            node_texts = [n.node.text for n in nodes]
            if node_texts:
                # Rerank and get top results
                reranked_results = RerankerFactory.predict(query, node_texts, top_k=limit)
                
                # Reconstruct sorted node list
                # reranked_results is list of (original_index, score)
                sorted_nodes = []
                for idx, score in reranked_results:
                    node = nodes[idx]
                    node.score = float(score)
                    sorted_nodes.append(node)
                
                results = sorted_nodes
            else:
                results = []
                
        except Exception as e:
            print(f"Reranking failed: {e}, falling back to hybrid results")
            results = nodes[:limit]
        
        # 6. Deduplicate by text content
        seen_texts = set()
        deduplicated = []
        for node_with_score in results:
            # Normalize text for comparison
            text = node_with_score.node.text if hasattr(node_with_score, 'node') else node_with_score.text
            normalized = text.strip().lower()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                deduplicated.append(node_with_score)
        
        # If we filtered too many, fetch more unique results from original candidates
        if len(deduplicated) < limit and len(nodes) > len(results):
            for node_with_score in nodes[len(results):]:
                if len(deduplicated) >= limit:
                    break
                text = node_with_score.node.text if hasattr(node_with_score, 'node') else node_with_score.text
                normalized = text.strip().lower()
                if normalized not in seen_texts:
                    seen_texts.add(normalized)
                    deduplicated.append(node_with_score)
        
        results = deduplicated[:limit]
        
        # 7. Format Response
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
