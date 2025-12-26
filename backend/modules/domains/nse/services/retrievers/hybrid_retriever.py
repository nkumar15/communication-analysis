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
        Async retrieval implementation using Client-Side RRF (Reciprocal Rank Fusion).
        This bypasses Elasticsearch license restrictions for server-side RRF.
        """
        if not self._tenant_id:
            raise ValueError("Tenant ID is required for TenantAwareHybridRetriever")

        query_text = query_bundle.query_str
        query_embedding = await self._embed_model.aget_query_embedding(query_text)
        
        # 1. Execute Parallel Searches (BM25 and kNN)
        
        # A. Keyword Search (BM25)
        bm25_query = {
            "query": {
                "bool": {
                    "must": [{"match": {"content": query_text}}],
                    "filter": [{"term": {"metadata.tenant_id.keyword": self._tenant_id}}]
                }
            },
            "size": 50, # Fetch more candidates for fusion
            "_source": ["content", "metadata", "id", "document_id"]
        }

        # B. Vector Search (kNN)
        knn_query = {
            "knn": {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": 50, # Fetch more candidates for fusion
                "num_candidates": 100,
                "filter": {"term": {"metadata.tenant_id.keyword": self._tenant_id}}
            },
            "size": 50,
            "_source": ["content", "metadata", "id", "document_id"]
        }
        
        import asyncio
        # Execute both requests concurrently
        responses = await asyncio.gather(
            self._client.search(index=self._index_name, body=bm25_query),
            self._client.search(index=self._index_name, body=knn_query)
        )
        
        bm25_hits = responses[0].get("hits", {}).get("hits", [])
        knn_hits = responses[1].get("hits", {}).get("hits", [])
        
        # 2. Perform Reciprocal Rank Fusion (RRF) in Python
        # Formula: score = 1.0 / (k + rank)
        rrf_k = 60
        doc_scores = {}
        doc_data = {}
        
        # Process BM25 Ranks
        for rank, hit in enumerate(bm25_hits):
            doc_id = hit["_id"]
            doc_data[doc_id] = hit
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        # Process kNN Ranks
        for rank, hit in enumerate(knn_hits):
            doc_id = hit["_id"]
            # If doc not in BM25 results, add it
            if doc_id not in doc_data:
                doc_data[doc_id] = hit
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            
        # 3. Sort and Form Nodes
        sorted_doc_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)[:self._top_k]
        
        nodes = []
        for doc_id in sorted_doc_ids:
            hit = doc_data[doc_id]
            source = hit.get("_source", {})
            score = doc_scores[doc_id]
            
            content = source.get("content", "")
            metadata = source.get("metadata", {})
            
            node = TextNode(
                text=content,
                metadata=metadata,
                id_=hit["_id"],
            )
            nodes.append(NodeWithScore(node=node, score=score))
            
        return nodes

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync wrapper fallback (should generally not be used in our async app)"""
        # LlamaIndex might call this if not awaited properly, but we use aget_relevant_documents usually?
        # We need an event loop wrapper if needed.
        # But simpler: raise error or use sync client.
        raise NotImplementedError("Use async retrieve (_aretrieve) for this retriever")
