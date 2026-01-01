"""
Ingestion Service

Handles document ingestion workflow - extracted from worker for testability.
Business logic separated from async/event loop management.
"""
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.constants import DocumentStatus
from core.db.rls import rls_service
from core.config import settings
from infrastructure.logging import get_logger
from modules.b2b.models.rag_document import RagDocument
from modules.domains.nse.services.rag_service import RagService
from modules.domains.nse.exceptions import IngestionError

logger = get_logger(__name__)


class IngestionService:
    """
    Service for document ingestion workflow.
    
    Extracted from worker to separate business logic from async/event loop handling.
    Worker handles ThreadPoolExecutor + event loop, this service handles the workflow.
    """
    
    async def process_ingestion(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        file_path: str,
        job_id: str,
        document_metadata: Dict[str, Any],
        content_hash: str,
        rag_service: RagService
    ) -> Dict[str, Any]:
        """
        Main ingestion workflow.
        
        Args:
            db: Database session (with RLS context already set by caller)
            tenant_id: Tenant UUID
            file_path: S3 path to document
            job_id: Job ID for status tracking
            document_metadata: Document metadata
            content_hash: SHA-256 hash for deduplication
            rag_service: Initialized RagService instance
            
        Returns:
            Dict with ingestion result (chunks, status, etc.)
            
        Raises:
            IngestionError: If ingestion fails
        """
        try:
            # 1. Find and validate document record
            rag_doc = await self._get_document_record(db, job_id)
            
            if not rag_doc:
                logger.warning("document_not_found", job_id=job_id)
                # Proceed anyway - document may have been created externally
            
            # 2. Check idempotency
            if rag_doc and await self._is_already_completed(rag_doc, job_id):
                return {"status": "skipped", "reason": "already_completed"}
            
            # 3. Check for duplicates
            if await self._is_duplicate(db, tenant_id, content_hash, rag_doc):
                return {"status": "skipped", "reason": "duplicate"}
            
            # 4. Update status to PROCESSING
            if rag_doc:
                await self._set_processing_status(db, rag_doc, tenant_id)
            
            # 5. Execute ingestion via RagService
            result = await rag_service.ingest_document(
                db=db,
                tenant_id=tenant_id,
                file_path=file_path,
                document_metadata=document_metadata
            )
            
            # 6. Update status to COMPLETED
            if rag_doc:
                await self._set_completed_status(
                    db=db,
                    rag_doc=rag_doc,
                    chunks=result.get('chunks', 0)
                )
            
            logger.info(
                "ingestion_success",
                file_path=file_path,
                chunks=result.get('chunks', 0),
                job_id=job_id
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "ingestion_failed",
                file_path=file_path,
                job_id=job_id,
                error=str(e),
                exc_info=True
            )
            
            # Update status to FAILED if we have a document record
            if 'rag_doc' in locals() and rag_doc:
                await self._set_failed_status(db, rag_doc, str(e))
            
            raise IngestionError(f"Document ingestion failed: {str(e)}") from e
    
    async def _get_document_record(
        self,
        db: AsyncSession,
        job_id: str
    ) -> RagDocument:
        """Find document by job_id."""
        stmt = select(RagDocument).where(RagDocument.job_id == job_id)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def _is_already_completed(
        self,
        rag_doc: RagDocument,
        job_id: str
    ) -> bool:
        """Check if document is already completed (idempotency)."""
        if rag_doc.status == DocumentStatus.COMPLETED.value:
            logger.info("job_already_completed", job_id=job_id)
            return True
        return False
    
    async def _is_duplicate(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        content_hash: str,
        rag_doc: RagDocument
    ) -> bool:
        """
        Check if document is a duplicate based on content hash.
        
        Returns True if duplicate found and document status updated.
        """
        if not content_hash or settings.rag_skip_deduplication:
            return False
        
        # Look for existing completed document with same hash
        duplicate_check = select(RagDocument).where(
            RagDocument.tenant_id == tenant_id,
            RagDocument.content_hash == content_hash,
            RagDocument.status == DocumentStatus.COMPLETED.value
        )
        duplicate_result = await db.execute(duplicate_check)
        existing_doc = duplicate_result.scalars().first()
        
        if existing_doc and rag_doc:
            logger.info(
                "duplicate_content_detected",
                content_hash_preview=content_hash[:8],
                existing_doc_id=str(existing_doc.id)
            )
            
            # Mark as completed (duplicate)
            rag_doc.status = DocumentStatus.COMPLETED.value
            rag_doc.chunk_count = existing_doc.chunk_count
            rag_doc.error_message = f"Duplicate of document {existing_doc.id}"
            await db.commit()
            return True
        
        return False
    
    async def _set_processing_status(
        self,
        db: AsyncSession,
        rag_doc: RagDocument,
        tenant_id: UUID
    ):
        """Update document status to PROCESSING."""
        rag_doc.status = DocumentStatus.PROCESSING.value
        await db.commit()
        
        # CRITICAL: RLS context lost after commit, re-apply
        await rls_service.set_tenant_context(db, tenant_id)
        
        logger.info("document_status_updated", document_id=str(rag_doc.id), status="processing")
    
    async def _set_completed_status(
        self,
        db: AsyncSession,
        rag_doc: RagDocument,
        chunks: int
    ):
        """Update document status to COMPLETED."""
        rag_doc.status = DocumentStatus.COMPLETED.value
        rag_doc.chunk_count = chunks
        rag_doc.error_message = None
        await db.commit()
    
    async def _set_failed_status(
        self,
        db: AsyncSession,
        rag_doc: RagDocument,
        error_message: str
    ):
        """Update document status to FAILED."""
        rag_doc.status = DocumentStatus.FAILED.value
        rag_doc.error_message = f"Processing failed: {error_message}"
        try:
            await db.commit()
        except Exception as db_exc:
            logger.error("failed_to_save_error_status", error=str(db_exc))


# Singleton instance
ingestion_service = IngestionService()
