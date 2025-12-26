import logging
import os
from typing import Dict, Any, List
from uuid import UUID
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession
from llama_index.core import VectorStoreIndex, StorageContext, Settings, SimpleDirectoryReader

from infrastructure.factories.llm_factory import LLMFactory
from infrastructure.factories.embedding_factory import EmbeddingFactory
from infrastructure.factories.vector_store_factory import VectorStoreFactory
from infrastructure.factories.storage_factory import StorageFactory

logger = logging.getLogger(__name__)

class BaseRagService(ABC):
    """
    Abstract Base Class for Domain-Specific RAG Services.
    Encapsulates common orchestration logic:
    - Infrastructure initialization (LLM, Embeddings, VectorStore)
    - File retrieval from MinIO/S3
    - Standard Ingestion Pipeline (Load -> Metadata -> Parse -> Index)
    """

    def __init__(self):
        # Lazy initialization
        self.llm = None
        self.embed_model = None
        self.vector_store = None
        self.storage_client = None

    @abstractmethod
    def get_index_name(self) -> str:
        """Return the Elasticsearch/VectorStore index name for this domain."""
        pass

    @abstractmethod
    def get_parser(self):
        """Return the domain-specific parser instance."""
        pass

    def _ensure_initialized(self):
        """Initialize components if not already done"""
        if not self.llm:
            self.llm = LLMFactory.get_llm()
            self.embed_model = EmbeddingFactory.get_embedding_model()
            
            # Use configured index name from abstract method
            index_name = self.get_index_name()
            self.vector_store = VectorStoreFactory.get_vector_store(index_name=index_name)
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
            documents = SimpleDirectoryReader(input_files=[processing_path]).load_data()
            
            # 2. Enrich Metadata
            for doc in documents:
                doc.metadata.update(document_metadata)
                doc.metadata["tenant_id"] = str(tenant_id)
            
            # 3. Parse & Chunk strategy (Delegated to Domain)
            parser = self.get_parser()
            nodes = parser.get_nodes_from_documents(documents)
            
            # 4. Create/Update Index (Ingest into Vector Store)
            VectorStoreIndex(
                nodes, 
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                show_progress=True
            )
            
            logger.info(f"Ingested {len(nodes)} chunks successfully to index '{self.get_index_name()}'")
            
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

    async def search(self, query: str, tenant_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        Generic search implementation. 
        Can be overridden by domains if they need specific query logic.
        """
        self._ensure_initialized()
        
        # Note: This is a basic implementation. 
        # Ideally we'd move the HybridRetriever logic here or into a factory too.
        # For now, we'll keep the advanced retriever logic in the specific service 
        # or refactor it next.
        pass
