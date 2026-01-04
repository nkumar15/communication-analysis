from llama_index.core.node_parser import SentenceSplitter
from typing import Dict, Any, List
from uuid import UUID
from modules.domains.core.services.base_rag_service import BaseRagService
from llama_index.core import VectorStoreIndex

class PolicyRagService(BaseRagService):
    _vector_store_provider = "elasticsearch"

    def get_index_name(self) -> str:
        return "enron_regulations"

    def get_parser(self):
        # Regulations are dense; smaller chunks might be better to pinpoint specific clauses
        return SentenceSplitter(chunk_size=256, chunk_overlap=20)

    async def search(self, query: str, limit: int = 3, **kwargs) -> Dict[str, Any]:
        """Search specifically for regulations."""
        self._ensure_initialized()
        
        index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
        retriever = index.as_retriever(similarity_top_k=limit)
        nodes = await retriever.aretrieve(query)
        
        return self._format_results(query, nodes)

    def _format_results(self, query: str, nodes: List) -> Dict[str, Any]:
        results = []
        for n in nodes:
            results.append({
                "text": n.node.get_content(),
                "source": n.node.metadata.get("filename", "unknown"),
                "score": n.score
            })
        
        return {
            "query": query,
            "results": results
        }

# Singleton
policy_rag_service = PolicyRagService()
