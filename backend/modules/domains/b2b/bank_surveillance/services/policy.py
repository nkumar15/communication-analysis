from llama_index.core.node_parser import SentenceSplitter
from typing import Dict, Any, List
from uuid import UUID
from modules.domains.shared.services.base_rag_service import BaseRagService
from llama_index.core import VectorStoreIndex

class PolicyRagService(BaseRagService):
    _vector_store_provider = "elasticsearch"

    def get_index_name(self) -> str:
        return "bank_compliance_regulations"

    def get_parser(self):
        # Regulations are dense; smaller chunks might be better to pinpoint specific clauses
        return SentenceSplitter(chunk_size=256, chunk_overlap=20)

    async def search(self, query: str, limit: int = 3, tenant_id: UUID = None, **kwargs) -> Dict[str, Any]:
        """
        Search specifically for regulations.
        
        Args:
            query: Search query
            limit: Number of results to return
            tenant_id: Tenant ID for filtering (required for multi-tenancy)
        """
        self._ensure_initialized()
        
        index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
        
        # Apply tenant filtering if tenant_id is provided
        if tenant_id:
            from llama_index.core.vector_stores import MetadataFilters, FilterCondition, MetadataFilter
            
            filters = MetadataFilters(
                filters=[
                    MetadataFilter(key="tenant_id", value=str(tenant_id), operator="==")
                ],
                condition=FilterCondition.AND
            )
            retriever = index.as_retriever(similarity_top_k=limit, filters=filters)
        else:
            # No filtering - search all regulations (useful for demos/testing)
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

    async def index_text(self, text: str, metadata: Dict[str, Any], doc_id: str = None) -> bool:
        """
        Index a single text document (regulation clause).
        Uses the configured embedding model (Semantic Search).
        """
        from llama_index.core import Document, StorageContext
        
        self._ensure_initialized()
        
        try:
            doc = Document(text=text, metadata=metadata, doc_id=doc_id)
            parser = self.get_parser()
            nodes = parser.get_nodes_from_documents([doc])
            
            # Use the initialized embedding model (Real Semantic Search for Regulations)
            embed_model = self.embed_model
            
            VectorStoreIndex(
                nodes,
                storage_context=StorageContext.from_defaults(vector_store=self.vector_store),
                embed_model=embed_model, 
                show_progress=False
            )
            return True
        except Exception as e:
            print(f"Policy indexing failed: {e}")
            return False

# Singleton
policy_rag_service = PolicyRagService()
