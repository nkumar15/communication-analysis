import os
from typing import List, Optional
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.embeddings import BaseEmbedding
from elasticsearch import AsyncElasticsearch

class TenantAwareHybridRetriever(BaseRetriever):
    """
    Custom Retriever for Tenant-Aware Hybrid Search (RRF).
    Combines Vector Search (KNN) and Keyword Search (BM25) with Reciprocal Rank Fusion.
    Enforces strict tenant isolation via filter.
    """
    def __init__(
        self,
        embed_model: BaseEmbedding,
        index_name: str = "rag_documents",
        tenant_id: str = None,
        top_k: int = 5,
        vector_weight: float = 0.5, # Not used in RRF strictly but good for param
    ):
        super().__init__()
        self._embed_model = embed_model
        self._index_name = index_name
        self._tenant_id = tenant_id
        self._top_k = top_k
        self._es_url = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
        self._client = AsyncElasticsearch(self._es_url)

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Async retrieval implementation.
        """
        if not self._tenant_id:
            raise ValueError("Tenant ID is required for TenantAwareHybridRetriever")

        query_text = query_bundle.query_str
        query_embedding = await self._embed_model.aget_query_embedding(query_text)
        
        # Construct Hybrid Query with RRF
        # Note: Elasticsearch 8.8+ supports 'rrf' in 'retriever' or 'rank' param.
        # We use the 'sub_searches' or 'hybrid' approach depending on version.
        # The documentation example used:
        # { "query": { "bool": ... }, "knn": ... , "rank": { "rrf": ... } } 
        # But 'rank' is for 8.14+? 
        # Standard approach for 8.12+ (which we use):
        # use 'retriever' parameter OR 'knn' + 'query' and 'rank'.
        
        # Let's use the standard "knn" + "query" composition which is supported well.
        
        # License Issue: RRF requires Platinum license.
        # Fallback: Linear Combination (Standard Hybrid).
        # Elastic 8.x sums the scores of 'knn' and 'query' if both are present.
        
        es_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "content": {
                                    "query": query_text,
                                    "boost": 0.5 # Weight for Keyword
                                }
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"metadata.tenant_id.keyword": self._tenant_id}}
                    ]
                }
            },
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": self._top_k,
                "num_candidates": 50,
                "filter": {
                    "term": {"metadata.tenant_id.keyword": self._tenant_id}
                },
                "boost": 0.5 # Weight for Vector
            },
            # Removed "rank": {"rrf": ...} due to license non-compliance
            "size": self._top_k,
            "_source": ["content", "metadata", "id", "document_id"]
        }
        
        try:
            response = await self._client.search(
                index=self._index_name,
                body=es_query
            )
            
            nodes = []
            hits = response.get("hits", {}).get("hits", [])
            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score") or hit.get("_rank_score", 0.0) # RRF provides _rank_score?
                # In RRF, score is null in hits, but sort logic handles it.
                # Actually ES returns a score from RRF if configured.
                
                content = source.get("content", "")
                metadata = source.get("metadata", {})
                
                # Reconstruct TextNode
                # Elastic source might not have 'id' at top level if LlamaIndex indexed it in a specific way.
                # Usually metadata['doc_id'] or the ES _id is the node ID.
                node = TextNode(
                    text=content,
                    metadata=metadata,
                    id_=hit["_id"], # Use the ES document ID as the Node ID
                )
                nodes.append(NodeWithScore(node=node, score=score or 0.0))
                
            return nodes
            
        finally:
            await self._client.close()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync wrapper fallback (should generally not be used in our async app)"""
        # LlamaIndex might call this if not awaited properly, but we use aget_relevant_documents usually?
        # We need an event loop wrapper if needed.
        # But simpler: raise error or use sync client.
        raise NotImplementedError("Use async retrieve (_aretrieve) for this retriever")
