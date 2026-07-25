import os
import logging
from typing import List, Optional, Any
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.vector_stores import MetadataFilters
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger(__name__)

class ElasticsearchBM25Retriever(BaseRetriever):
    """
    Custom Retriever for Keyword Search (BM25) using Elasticsearch.
    Enforces strict tenant isolation and supports metadata filters.
    """
    def __init__(
        self,
        index_name: str,
        tenant_id: str,
        filters: Optional[MetadataFilters] = None,
        top_k: int = 50, # Retrieve more candidates for fusion
    ):
        super().__init__()
        self._index_name = index_name
        self._tenant_id = tenant_id
        self._filters = filters
        self._top_k = top_k
        self._es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        self._client = AsyncElasticsearch(self._es_url)

    def _build_es_filters(self) -> List[dict]:
        """
        Constructs Elasticsearch filter clauses from tenant_id and optional MetadataFilters.
        """
        # 1. Mandatory Tenant Isolation
        es_filters = [{"term": {"metadata.tenant_id.keyword": self._tenant_id}}]
        
        # 2. Dynamic Metadata Filters
        if self._filters and self._filters.filters:
            for f in self._filters.filters:
                # Assuming simple exact match for now. Use .keyword for exact string fields.
                # LlamaIndex filters have key, value, operator.
                field_name = f"metadata.{f.key}.keyword" if isinstance(f.value, str) else f"metadata.{f.key}"
                es_filters.append({"term": {field_name: f.value}})
                
        return es_filters

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        if not self._tenant_id:
             raise ValueError("Tenant ID is required for ElasticsearchBM25Retriever")

        query_text = query_bundle.query_str
        filter_clauses = self._build_es_filters()
        
        # Keyword Search (BM25)
        bm25_query = {
            "query": {
                "bool": {
                    "must": [{"match": {"content": query_text}}],
                    "filter": filter_clauses
                }
            },
            "size": self._top_k, 
            "_source": ["content", "metadata", "id", "document_id"]
        }
        
        try:
            response = await self._client.search(index=self._index_name, body=bm25_query)
            hits = response.get("hits", {}).get("hits", [])
            
            nodes = []
            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score", 0.0)
                
                content = source.get("content", "")
                metadata = source.get("metadata", {})
                
                node = TextNode(
                    text=content,
                    metadata=metadata,
                    id_=hit["_id"],
                )
                nodes.append(NodeWithScore(node=node, score=score))
                
            return nodes
            
        finally:
            # We don't close the client here as it might be expensive to create/destroy repeatedly.
            # Ideally this client should be shared or managed by a factory, but for now we let it be collected.
             await self._client.close()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        raise NotImplementedError("Use async retrieve (_aretrieve) for this retriever")
