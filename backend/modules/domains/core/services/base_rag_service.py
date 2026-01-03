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

    async def _enrich_metadata_hook(self, documents: List[Any]) -> Dict[str, Any]:
        """
        Optional hook to extract or enrich metadata from loaded documents *before* processing.
        Override this in subclasses if needed.
        """
        return {}

    def _ensure_initialized(self):
        """Initialize components if not already done"""
        if not self.llm:
            self.llm = LLMFactory.get_llm()
            self.embed_model = EmbeddingFactory.get_embedding_model()
            
            # Use configured index name from abstract method
            index_name = self.get_index_name()
            # Explicitly favor instance-specific provider config, or fallback to factory default
            self.vector_store = VectorStoreFactory.get_vector_store(
                index_name=index_name, 
                provider=getattr(self, "_vector_store_provider", None)
            )
            self.storage_client = StorageFactory.get_storage_client()
            
            # Setup Global LlamaIndex Settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model

    async def _delete_existing_documents(self, tenant_id: UUID, content_hash: str):
        """
        Delete existing documents from Vector Store to prevent duplication.
        Uses content_hash to reliably identify exact duplicates even if filename differs.
        """
        if not self.vector_store:
            return

        try:
            # Check for ElasticsearchStore
            # We check class name string to avoid importing if not needed, or try/except
            if "ElasticsearchStore" in self.vector_store.__class__.__name__:
                es_client = getattr(self.vector_store, "client", None)
                if not es_client:
                    return

                index_name = self.get_index_name()
                
                # Query matches tenant_id AND content_hash
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"metadata.tenant_id.keyword": str(tenant_id)}},
                                {"term": {"metadata.content_hash.keyword": content_hash}}
                            ]
                        }
                    }
                }
                
                logger.info(f"Deleting existing vectors for hash {content_hash[:8]}... in index {index_name}")
                
                # Check for async client
                # Check for async client
                if hasattr(es_client, "delete_by_query") and callable(es_client.delete_by_query):
                    import inspect
                    res = es_client.delete_by_query(index=index_name, body=query, refresh=True)
                    if inspect.isawaitable(res):
                        await res

        except Exception as e:
            logger.warning(f"Failed to delete existing vectors: {e}")

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
        
        # 0. Delete Existing Vectors (Deduplication by Content Hash)
        content_hash = document_metadata.get("content_hash")
        if content_hash:
             await self._delete_existing_documents(tenant_id, content_hash)
        
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
            
            # HOOK: Domain-specific metadata enrichment (e.g. Extract Ticker from content)
            extracted_metadata = await self._enrich_metadata_hook(documents)
            if extracted_metadata:
                logger.info(f"Extracted metadata: {extracted_metadata}")
                document_metadata.update(extracted_metadata)

            # 2. Enrich Metadata
            for doc in documents:
                doc.metadata.update(document_metadata)
                doc.metadata["tenant_id"] = str(tenant_id)
                # Fix for temp filename citations
                if "original_filename" in document_metadata:
                    doc.metadata["file_name"] = document_metadata["original_filename"]
                    doc.metadata["filename"] = document_metadata["original_filename"]
                
                # Ensure content_hash is in metadata (critical for future deletions)
                if content_hash and "content_hash" not in doc.metadata:
                    doc.metadata["content_hash"] = content_hash
            
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
        return 

    async def close(self):
        """
        Cleanup resources (clients, sessions) to avoid warnings/leaks.
        """
        # Close Vector Store Client
        if self.vector_store:
            # Check for close/aclose methods on vector_store or its client
            if hasattr(self.vector_store, "close"):
                try:
                    res = self.vector_store.close()
                    if hasattr(res, "__await__"):
                        await res
                except Exception as e:
                    logger.warning(f"Error closing vector_store: {e}")
            
            # Check for client inside vector store (common in ElasticsearchStore)
            if hasattr(self.vector_store, "client"):
                client = getattr(self.vector_store, "client")
                if hasattr(client, "close"):
                    try:
                        res = client.close()
                        if hasattr(res, "__await__"):
                            await res
                    except Exception as e:
                        logger.warning(f"Error closing vector_store client: {e}")

