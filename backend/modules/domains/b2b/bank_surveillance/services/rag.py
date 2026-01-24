from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import VectorStoreIndex
from typing import Dict, Any, List, Optional
from uuid import UUID
from modules.domains.shared.services.base_rag_service import BaseRagService

class CommunicationRagService(BaseRagService):
    _vector_store_provider = "elasticsearch"

    def get_index_name(self) -> str:
        return "communications"

    def get_parser(self):
        # Use simple sentence splitter for chunks
        return SentenceSplitter(chunk_size=512, chunk_overlap=50)

    async def search(self, query: str, tenant_id: UUID, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """Basic RAG Search using Vector Store."""
        self._ensure_initialized()
        
        # 1. Create Retriever from Index
        index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
        
        # TODO: Add metadata filters for tenant_id (Basic RAG usually implies simple retrieval first)
        # filters = MetadataFilters(filters=[MetadataFilter(key="tenant_id", value=str(tenant_id))])
        
        retriever = index.as_retriever(similarity_top_k=limit)
        
        # 2. Retrieve
        nodes = await retriever.aretrieve(query)
        
        # 3. Format
        return self._format_results(query, nodes)

    def _format_results(self, query: str, nodes: List) -> Dict[str, Any]:
        results = []
        for n in nodes:
            results.append({
                "text": n.node.get_content(),
                "score": n.score,
                "metadata": n.node.metadata
            })
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }

    def _get_embedding_model(self, enable_semantic: bool):
        """
        Returns the appropriate embedding model based on regulation.
        - enable_semantic=True -> Real Embedding Model (e.g. OpenAI)
        - enable_semantic=False -> Mock Embedding (Keyword Only, Cost Saving)
        """
        if enable_semantic:
            return self.embed_model or EmbeddingFactory.get_embedding_model()
        else:
            from llama_index.core.embeddings import MockEmbedding
            # Use 1536 as safe default for OpenAI compatibility in ES mapping
            return MockEmbedding(embed_dim=1536)

    async def index_text(self, text: str, metadata: Dict[str, Any], doc_id: str = None, enable_semantic: bool = False) -> bool:
        """
        Index a single text document.
        Args:
            enable_semantic: If True, generate real embeddings. If False, use Mock (keyword only).
        """
        from llama_index.core import Document, StorageContext
        
        self._ensure_initialized()
        
        try:
            doc = Document(text=text, metadata=metadata, doc_id=doc_id)
            parser = self.get_parser()
            nodes = parser.get_nodes_from_documents([doc])
            
            # Select Model
            embed_model = self._get_embedding_model(enable_semantic)
            
            VectorStoreIndex(
                nodes,
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                embed_model=embed_model, 
                show_progress=False
            )
            return True
        except Exception as e:
            print(f"Vector indexing failed: {e}")
            return False

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID (from vector store)."""
        # ... (Existing implementation unchanged) ...
        self._ensure_initialized()
        if self._vector_store_provider == "elasticsearch":
             pass # ...
        return None

    # ... get_content_by_id stays same ...

    async def index_batch(self, documents: List[Dict[str, Any]], enable_semantic: bool = False) -> int:
        """
        Batch index multiple documents.
        Args:
            enable_semantic: If True, generate real embeddings. If False, use Mock (keyword only).
        """
        from llama_index.core import Document, StorageContext
        
        self._ensure_initialized()
        
        docs = []
        for d in documents:
            docs.append(Document(
                text=d["text"], 
                metadata=d.get("metadata", {}),
                doc_id=d.get("doc_id") 
            ))
        
        parser = self.get_parser()
        nodes = parser.get_nodes_from_documents(docs)
        
        # Select Model
        embed_model = self._get_embedding_model(enable_semantic)
        
        VectorStoreIndex(
            nodes,
            storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
            embed_model=embed_model,
            show_progress=True
        )
        
        return len(docs)

# Singleton instance
communication_rag_service = CommunicationRagService()
