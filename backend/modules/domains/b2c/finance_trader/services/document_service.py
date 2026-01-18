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

from core.db.rls import rls_service
from core.config import settings
from core.constants import DocumentStatus, RAGDefaults
from infrastructure.factories.storage_factory import StorageFactory
from infrastructure.logging import get_logger
from infrastructure.monitoring import increment
from modules.b2b.models.rag_document import RagDocument
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
        tenant_id: UUID,
        file: UploadFile,
        metadata: Dict[str, Any]
    ) -> DocumentUploadResult:
        """
        Handle complete document upload flow.
        
        Args:
            db: Database session
            tenant_id: Tenant UUID
            file: Uploaded file
            metadata: Document metadata (company_name, report_type, etc.)
            
        Returns:
            DocumentUploadResult with job_id and document_id
            
        Raises:
            DocumentUploadError: If upload fails
        """
        try:
            # Set RLS context
            await rls_service.set_tenant_context(db, tenant_id)
            
            # 1. Read and hash content
            content = await file.read()
            content_hash = self._compute_hash(content)
            file_size = len(content)
            
            logger.info(
                "document_processing_started",
                filename=file.filename,
                file_size=file_size,
                content_hash_preview=content_hash[:8]
            )
            
            # 2. Upload to storage
            s3_path = await self._upload_to_storage(
                content=content,
                tenant_id=str(tenant_id),
                filename=file.filename,
                content_hash=content_hash,
                content_type=file.content_type
            )
            
            # 3. Create database record
            job_id = str(uuid.uuid4())
            doc = await self._create_document_record(
                db=db,
                tenant_id=tenant_id,
                file=file,
                s3_path=s3_path,
                file_size=file_size,
                content_hash=content_hash,
                job_id=job_id,
                metadata=metadata
            )
            
            # 4. Dispatch ingestion task
            await self._dispatch_ingestion_task(
                tenant_id=str(tenant_id),
                s3_path=s3_path,
                job_id=job_id,
                content_hash=content_hash,
                metadata=metadata
            )
            
            # 5. Record metrics
            increment("rag_document_uploads", labels={"domain": "nse", "status": "success"})
            
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
            increment("rag_document_uploads", labels={"domain": "nse", "status": "failed"})
            raise DocumentUploadError(f"Failed to upload document: {str(e)}") from e
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    async def _upload_to_storage(
        self,
        content: bytes,
        tenant_id: str,
        filename: str,
        content_hash: str,
        content_type: str
    ) -> str:
        """
        Upload content to MinIO object storage.
        
        Returns:
            S3 path string (s3://bucket/object_name)
        """
        storage = StorageFactory.get_storage_client()
        bucket = RAGDefaults.STORAGE_BUCKET
        
        # Ensure bucket exists
        if not storage.bucket_exists(bucket):
            storage.make_bucket(bucket)
            logger.info("storage_bucket_created", bucket=bucket)
        
        # Create object name with tenant isolation
        object_name = f"{tenant_id}/{content_hash}/{filename}"
        
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
        tenant_id: UUID,
        file: UploadFile,
        s3_path: str,
        file_size: int,
        content_hash: str,
        job_id: str,
        metadata: Dict[str, Any]
    ) -> RagDocument:
        """Create RagDocument database record."""
        new_doc = RagDocument(
            tenant_id=tenant_id,
            filename=file.filename,
            file_url=s3_path,
            file_size_bytes=file_size,
            mime_type=file.content_type,
            company_name=metadata.get("company_name"),
            report_type=metadata.get("report_type"),
            financial_period=metadata.get("financial_period"),
            status=DocumentStatus.PENDING.value,
            content_hash=content_hash,
            job_id=job_id
        )
        
        db.add(new_doc)
        await db.commit()
        
        return new_doc
    
    async def _dispatch_ingestion_task(
        self,
        tenant_id: str,
        s3_path: str,
        job_id: str,
        content_hash: str,
        metadata: Dict[str, Any]
    ):
        """Dispatch Celery task for background ingestion."""
        payload = {
            "tenant_id": tenant_id,
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
            "domain.ingest_document",
            args=[payload],
            queue="domain"
        )
        
        logger.debug("ingestion_task_dispatched", job_id=job_id)


# Singleton instance
document_service = DocumentService()
