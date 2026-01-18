import logging
from typing import List, Optional
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever, QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.schema import QueryBundle, NodeWithScore
from llama_index.core.settings import Settings

# Reuse existing ES BM25 Retriever
from modules.domains.b2c.finance_trader.services.retrievers.es_bm25_retriever import ElasticsearchBM25Retriever

logger = logging.getLogger(__name__)

class TenantAwareHybridRetriever(BaseRetriever):
    """
    Hybrid Retriever (Vector + BM25) with Tenant Isolation.
    Replicates the logic of RagService but is configurable for experiments.
    """
    def __init__(
        self,
        embed_model,
        tenant_id: str,
        index_name: str = "nse_rag_documents",
        top_k: int = 20,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
    ):
        super().__init__()
        self._embed_model = embed_model
        self._tenant_id = tenant_id
        self._index_name = index_name
        self._top_k = top_k
        self._weights = [vector_weight, bm25_weight]
        
        # Initialize Fusion Retriever
        self._fusion_retriever = self._build_retriever()

    def _build_retriever(self) -> BaseRetriever:
        try:
            # We need to access the VectorStore. 
            # Assuming we can get it from storage context or factory?
            # RagService uses: self.vector_store
            # Helper to get global vector store:
            from infrastructure.factories.vector_store_factory import VectorStoreFactory
            vector_store = VectorStoreFactory.get_vector_store(self._index_name)
            
            index = VectorStoreIndex.from_vector_store(
                vector_store, 
                embed_model=self._embed_model
            )
            
            # 1. Vector Retriever
            # Note: filters=None for now. Experimentation likely assumes access to all docs for tenant.
            # If we need filters logic (from query decomposition), we need to inject it.
            # For "gold_dataset", usually queries imply context.
            # Use tenant_id filter if VectorStore requires it? 
            # PGVector (likely used) handles tenant isolation via metadata filters?
            # Yes, usually. We need to construct a filter for tenant_id.
            from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
            tenant_filter = MetadataFilters(
                filters=[MetadataFilter(key="tenant_id", value=self._tenant_id)]
            )
            
            vector_retriever = index.as_retriever(
                filters=tenant_filter,
                similarity_top_k=self._top_k
            )
            
            # 2. BM25 Retriever
            bm25_retriever = ElasticsearchBM25Retriever(
                index_name=self._index_name,
                tenant_id=self._tenant_id,
                filters=tenant_filter,
                top_k=self._top_k
            )
            
            # 3. Fusion
            fusion_retriever = QueryFusionRetriever(
                [vector_retriever, bm25_retriever],
                retriever_weights=self._weights,
                similarity_top_k=self._top_k, 
                num_queries=1,
                mode=FUSION_MODES.RECIPROCAL_RANK,
                use_async=True
            )
            return fusion_retriever
            
        except Exception as e:
            logger.error(f"Failed to build HybridRetriever: {e}")
            raise

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        return await self._fusion_retriever.aretrieve(query_bundle)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        # Sync wrapper if needed, but we use async
        raise NotImplementedError("Use async")
