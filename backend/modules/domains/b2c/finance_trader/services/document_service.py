"""
Document Service

Handles document upload, storage, and management operations.
Extracted from router to improve testability and maintainability.
"""
import hashlib
import uuid
import io
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import UploadFile, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession
from celery import Celery

# from core.db.rls import rls_service # B2C might not use RLS yet
from core.config import settings
from core.constants import DocumentStatus, RAGDefaults
from infrastructure.factories.storage_factory import StorageFactory
from infrastructure.logging import get_logger
from infrastructure.monitoring import increment
# USE B2C MODEL
from modules.domains.b2c.finance_trader.models.rag_document import RagDocument
from modules.domains.b2c.finance_trader.exceptions import DocumentUploadError

logger = get_logger(__name__)

# Celery producer for task dispatch
celery_producer = Celery('api_producer', broker=settings.celery_broker_url_resolved)


class DocumentUploadResult:
    """Result of document upload operation."""
    def __init__(self, job_id: str, document_id: str, status: str):
        self.job_id = job_id
        self.document_id = document_id
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "status": self.status,
            "message": "Upload successful, ingestion started."
        }


class DocumentService:
    """Service for document upload and management operations."""
    
    async def upload_document(
        self,
        db: AsyncSession,
        workspace_id: UUID,  # Changed from tenant_id
        file: UploadFile,
        metadata: Dict[str, Any],
        uploaded_by: Optional[UUID] = None
    ) -> DocumentUploadResult:
        """
        Handle complete document upload flow.
        """
        try:
            # Note: B2C might not have explicit RLS call here if using workspace_id in query
            # await rls_service.set_tenant_context(db, tenant_id)
            
            # 1. Read and hash content
            content = await file.read()
            content_hash = self._compute_hash(content)
            file_size = len(content)
            
            logger.info(
                "document_processing_started",
                filename=file.filename,
                file_size=file_size,
                content_hash_preview=content_hash[:8],
                workspace_id=str(workspace_id)
            )
            
            # 2. Upload to storage (Using workspace_id as isolation prefix)
            s3_path = await self._upload_to_storage(
                content=content,
                isolation_id=str(workspace_id),
                filename=file.filename,
                content_hash=content_hash,
                content_type=file.content_type
            )
            
            # 3. Create database record
            job_id = str(uuid.uuid4())
            doc = await self._create_document_record(
                db=db,
                workspace_id=workspace_id,
                file=file,
                s3_path=s3_path,
                file_size=file_size,
                content_hash=content_hash,
                job_id=job_id,
                metadata=metadata,
                uploaded_by=uploaded_by
            )
            
            # 4. Dispatch ingestion task
            await self._dispatch_ingestion_task(
                workspace_id=str(workspace_id),
                s3_path=s3_path,
                job_id=job_id,
                content_hash=content_hash,
                metadata=metadata
            )
            
            # 5. Record metrics
            increment("rag_document_uploads", labels={"domain": "finance_trader", "status": "success"})
            
            logger.info(
                "document_upload_complete",
                job_id=job_id,
                document_id=str(doc.id)
            )
            
            return DocumentUploadResult(
                job_id=job_id,
                document_id=str(doc.id),
                status=DocumentStatus.PENDING.value
            )
            
        except Exception as e:
            logger.error(
                "document_upload_failed",
                filename=file.filename,
                error=str(e),
                exc_info=True
            )
            increment("rag_document_uploads", labels={"domain": "finance_trader", "status": "failed"})
            raise DocumentUploadError(f"Failed to upload document: {str(e)}") from e
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    async def _upload_to_storage(
        self,
        content: bytes,
        isolation_id: str,
        filename: str,
        content_hash: str,
        content_type: str
    ) -> str:
        """
        Upload content to MinIO object storage.
        """
        storage = StorageFactory.get_storage_client()
        bucket = RAGDefaults.STORAGE_BUCKET
        
        # Ensure bucket exists
        if not storage.bucket_exists(bucket):
            storage.make_bucket(bucket)
            logger.info("storage_bucket_created", bucket=bucket)
        
        # Create object name with workspace isolation
        object_name = f"{isolation_id}/{content_hash}/{filename}"
        
        # Upload
        file_stream = io.BytesIO(content)
        storage.put_object(
            bucket,
            object_name,
            file_stream,
            length=len(content),
            content_type=content_type
        )
        
        s3_path = f"s3://{bucket}/{object_name}"
        logger.debug("storage_upload_complete", s3_path=s3_path)
        
        return s3_path
    
    async def _create_document_record(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        file: UploadFile,
        s3_path: str,
        file_size: int,
        content_hash: str,
        job_id: str,
        metadata: Dict[str, Any],
        uploaded_by: Optional[UUID]
    ) -> RagDocument:
        """Create RagDocument database record."""
        new_doc = RagDocument(
            workspace_id=workspace_id,
            filename=file.filename,
            file_url=s3_path,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            company_name=metadata.get("company_name"),
            report_type=metadata.get("report_type"),
            financial_period=metadata.get("financial_period"),
            status=DocumentStatus.PENDING.value,
            content_hash=content_hash,
            job_id=job_id,
            uploaded_by=uploaded_by
        )
        
        db.add(new_doc)
        await db.commit()
        
        return new_doc
    
    async def _dispatch_ingestion_task(
        self,
        workspace_id: str,
        s3_path: str,
        job_id: str,
        content_hash: str,
        metadata: Dict[str, Any]
    ):
        """Dispatch Celery task for background ingestion."""
        payload = {
            "workspace_id": workspace_id,
            "file_path": s3_path,
            "job_id": job_id,
            "content_hash": content_hash,
            "document_metadata": {
                **metadata,
                "source": metadata.get("original_filename", "unknown"),
                "original_filename": metadata.get("original_filename", "unknown"),
                "content_hash": content_hash
            }
        }
        
        celery_producer.send_task(
            "b2c_domain.ingest_document",
            args=[payload],
            queue="b2c-domain"
        )
        
        logger.debug("ingestion_task_dispatched", job_id=job_id)


# Singleton instance
document_service = DocumentService()
