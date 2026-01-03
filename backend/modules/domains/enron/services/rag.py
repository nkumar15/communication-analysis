from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import VectorStoreIndex
from typing import Dict, Any, List
from uuid import UUID
from backend.modules.domains.core.services.base_rag_service import BaseRagService

class EnronRagService(BaseRagService):
    _vector_store_provider = "elasticsearch"

    def get_index_name(self) -> str:
        return "enron_emails"

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

# Singleton instance
enron_rag_service = EnronRagService()
