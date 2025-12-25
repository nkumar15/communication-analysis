import logging
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from llama_index.core import VectorStoreIndex, StorageContext, Settings, SimpleDirectoryReader

from infrastructure.factories.llm_factory import LLMFactory
from infrastructure.factories.embedding_factory import EmbeddingFactory
from infrastructure.factories.vector_store_factory import VectorStoreFactory
from infrastructure.factories.storage_factory import StorageFactory
from modules.domains.nse.services.parsers.nse_parser import NSEEarningsParser

logger = logging.getLogger(__name__)

class RagService:
    """
    Orchestrates the RAG ingestion pipeline for NSE Domain.
    Uses generic factories for infrastructure and NSE-specific parser.
    """
    
    def __init__(self):
        # Lazy initialization
        self.llm = None
        self.embed_model = None
        self.vector_store = None
        self.storage_client = None

    def _ensure_initialized(self):
        """Initialize components if not already done"""
        if not self.llm:
            self.llm = LLMFactory.get_llm()
            self.embed_model = EmbeddingFactory.get_embedding_model()
            
            # Use 'rag_documents' index/table. 
            self.vector_store = VectorStoreFactory.get_vector_store(index_name="rag_documents")
            self.storage_client = StorageFactory.get_storage_client()
            
            # Setup Global LlamaIndex Settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model

    async def ingest_document(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        file_path: str,
        document_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for document ingestion.
        """
        self._ensure_initialized()
        document_metadata = document_metadata or {}
        
        logger.info(f"Starting ingestion for tenant {tenant_id}, file: {file_path}")
        
        # Handle MinIO/S3 paths
        temp_file_path = None
        processing_path = file_path
        
        if file_path.startswith("s3://"):
             try:
                import tempfile
                bucket_name = file_path.replace("s3://", "").split("/")[0]
                object_name = "/".join(file_path.replace("s3://", "").split("/")[1:])
                
                # Create temp file
                ext = os.path.splitext(object_name)[1]
                temp_fd, temp_file_path = tempfile.mkstemp(suffix=ext)
                os.close(temp_fd)
                
                logger.info(f"Downloading {object_name} from bucket {bucket_name} to {temp_file_path}")
                self.storage_client.fget_object(bucket_name, object_name, temp_file_path)
                processing_path = temp_file_path
             except Exception as e:
                 logger.error(f"Failed to download from MinIO: {e}")
                 if temp_file_path and os.path.exists(temp_file_path):
                     os.remove(temp_file_path)
                 raise

        try:
            # 1. Load Data
            # Using SimpleDirectoryReader to load the file as Document objects
            documents = SimpleDirectoryReader(input_files=[processing_path]).load_data()
            
            # 2. Enrich Metadata
            for doc in documents:
                doc.metadata.update(document_metadata)
                doc.metadata["tenant_id"] = str(tenant_id)
            
            # 3. Parse & Chunk
            # Use specialized NSE Parser
            parser = NSEEarningsParser()
            nodes = parser.get_nodes_from_documents(documents)
            
            # 4. Create/Update Index (Ingest into Vector Store)
            # This handles embedding generation via Settings.embed_model
            VectorStoreIndex(
                nodes, 
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                show_progress=True
            )
            
            logger.info(f"Ingested {len(nodes)} chunks successfully")
            
            return {
                "status": "success", 
                "file_path": file_path, 
                "chunks": len(nodes),
                "tenant_id": str(tenant_id),
                "source": "minio" if temp_file_path else "local"
            }
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise
        finally:
            # Cleanup temp file
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

rag_service = RagService()
