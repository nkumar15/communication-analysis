import logging
from typing import Dict, Any, List, Optional
import asyncio
from uuid import UUID

from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

# from llama_index.llms.openai import OpenAI # REMOVED: Incompatible with uvloop
# from llama_index.core.llms import ChatMessage # REMOVED

from core.constants import RAGDefaults
from infrastructure.logging import get_logger
from modules.domains.core.services.base_rag_service import BaseRagService
from modules.domains.nse.services.parsers.nse_parser import NSEEarningsParser
from modules.domains.nse.services.parsers.metadata import NSEDocumentMetadata


logger = get_logger(__name__)

class RagService(BaseRagService):
    """
    NSE Domain Specific RAG Service.
    Extends BaseRagService to provide NSE-specific parser and configuration.
    Now includes 'Query Understanding' layer to extract metadata filters.
    """
    
    def __init__(self, index_name: str = "nse_rag_documents"):
        super().__init__()
        self._index_name = index_name
        
        # Preload Reranker Model to avoid latency on first request
        try:
             from infrastructure.factories.reranker_factory import RerankerFactory
             logger.info("Preloading Reranker model...")
             RerankerFactory.get_reranker()
             logger.info("Reranker model preloaded.")
        except Exception as e:
             logger.warning(f"Failed to preload reranker: {e}")

    def get_index_name(self) -> str:
        return self._index_name

    def get_parser(self):
        self._ensure_initialized()
        return NSEEarningsParser(embed_model=self.embed_model)

    async def _enrich_metadata_hook(self, documents: List[Any]) -> Dict[str, Any]:
        """
        Extract NSE specific metadata (Ticker, FY, Quarter) from the first page.
        """
        if not documents:
            return {}
            
        try:
            # Import here to avoid circular dependencies if any
            from modules.domains.nse.services.parsers.metadata import MetadataExtractor
            
            # Use the text of the first 3 pages to increase chance of finding company name
            # (Page 1 might be just a logo/image)
            pages_to_scan = documents[:RAGDefaults.METADATA_PAGES_TO_SCAN]
            combined_text = "\n---PAGE BREAK---\n".join([d.text for d in pages_to_scan])
            
            file_name = documents[0].metadata.get("file_name") or documents[0].metadata.get("filename")
            
            if len(combined_text) < 100:
                logger.warning(f"[MetadataEnrichment] Combined text too short: {len(combined_text)}")
            
            extractor = MetadataExtractor()
            # Run extraction with expanded context (3 pages)
            metadata_model = extractor.extract(combined_text)
            
            # Convert Pydantic to dict, filtering out None
            data = metadata_model.model_dump(exclude_none=True)
            
            # Flatten Scope list to single string if needed, or keep as list
            # ES schema might expect keyword. Let's keep it as is, BaseRagService handles it as metadata dict.
            
            return data
            
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            logger.error(f"Metadata extraction traceback", exc_info=True)
            return {}

    async def _decompose_query(self, query_text: str) -> Optional[MetadataFilters]:
        """
        Uses LLM to extract metadata filters (Ticker, Year, Scope) from natural language query.
        Example: "Revenue of TCS in FY25" -> {ticker: TCS, fiscal_year: FY25}
        """
        try:
            from llama_index.core import Settings
            
            prompt_template_str = (
                "You are an expert financial query parser. Your job is to extract search filters from the user's natural language question.\n"
                "Target Metadata Fields:\n"
                "- ticker: The stock ticker symbol of the company explicitly mentioned (e.g., 'reliance' -> 'RELIANCE', 'tcs' -> 'TCS').\n"
                "- fiscal_year: The Fiscal Year if mentioned (e.g., 'FY25', '2025').\n"
                "- quarter: The Quarter if mentioned (e.g., 'Q2', 'second quarter').\n"
                "- scope: 'Standalone' or 'Consolidated' if strictly mentioned.\n\n"
                "Rules:\n"
                "1. If a company name is mentioned (even in lowercase like 'reliance'), extract its standard ticker (e.g. RELIANCE).\n"
                "2. Specific Mappings: 'HDFC' or 'HDFC Bank' -> 'HDFCBANK', 'Reliance' -> 'RELIANCE'.\n"
                "3. If no company is mentioned, leave ticker null.\n"
                "4. Do not infer filters that are not in the query.\n\n"
                "User Question: {query_str}\n"
            )

            # Use LlamaIndex's built-in structured prediction
            from llama_index.core import PromptTemplate
            output = await Settings.llm.astructured_predict(
                NSEDocumentMetadata,
                PromptTemplate(prompt_template_str),
                query_str=query_text
            )
            
            filters = []
            if output.ticker:
                filters.append(MetadataFilter(key="ticker", value=output.ticker))
            if output.fiscal_year:
                filters.append(MetadataFilter(key="fiscal_year", value=output.fiscal_year))
            if output.quarter:
                filters.append(MetadataFilter(key="quarter", value=output.quarter))
            # Scope is list, handle single if present (simplification)
            if output.scope and output.scope[0] != "Unknown":
                 filters.append(MetadataFilter(key="scope", value=output.scope[0]))

            if not filters:
                return None
                
            logger.info(f"[QueryDecomposer] Extracted Filters: {filters}")
            return MetadataFilters(filters=filters)

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}")
            return None

    async def search(self, query: str, tenant_id: UUID, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Main search orchestration method.
        
        Args:
            query: Search query
            tenant_id: Tenant UUID for isolation
            limit: Number of final results to return
            
        Returns:
            Dict with query, filters, results, and count
        """
        self._ensure_initialized()
        
        # 1. Decompose query into metadata filters
        filters = await self._decompose_query(query)
        logger.info("query_decomposed", query_preview=query[:50], has_filters=bool(filters))
        
        # 2. Retrieve candidates using hybrid search
        candidates = await self._retrieve_candidates(query, tenant_id, filters)
        
        # 3. Deduplicate nodes
        unique_candidates = self._deduplicate_nodes(candidates)
        
        # 4. Rerank results
        ranked_results = await self._rerank_results(query, unique_candidates, limit)
        
        # 5. Format and return
        return self._format_search_results(query, ranked_results, filters)
    
    async def _retrieve_candidates(
        self,
        query: str,
        tenant_id: UUID,
        filters: Optional[MetadataFilters]
    ) -> List:
        """
        Retrieve candidates using hybrid search (vector + BM25).
        
        Returns:
            List of NodeWithScore objects
        """
        from llama_index.core.retrievers import QueryFusionRetriever
        from llama_index.core import VectorStoreIndex
        from modules.domains.nse.services.retrievers.es_bm25_retriever import ElasticsearchBM25Retriever
        from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
        from llama_index.core.schema import QueryBundle
        from infrastructure.monitoring import record_rag_processing
        
        # Create vector retriever
        index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
        vector_retriever = index.as_retriever(
            filters=filters,
            similarity_top_k=RAGDefaults.VECTOR_TOP_K
        )
        
        # Create BM25 retriever
        bm25_retriever = ElasticsearchBM25Retriever(
            index_name=self.get_index_name(),
            tenant_id=str(tenant_id),
            filters=filters,
            top_k=RAGDefaults.BM25_TOP_K
        )
        
        # Create fusion retriever
        fusion_retriever = QueryFusionRetriever(
            [vector_retriever, bm25_retriever],
            retriever_weights=[RAGDefaults.VECTOR_WEIGHT, RAGDefaults.BM25_WEIGHT],
            similarity_top_k=RAGDefaults.FUSION_TOP_K,
            num_queries=1,
            mode=FUSION_MODES.RECIPROCAL_RANK,
            use_async=True
        )
        
        # Execute retrieval with monitoring
        logger.info("retrieval_started", query_preview=query[:50])
        with record_rag_processing(domain="nse", stage="retrieval"):
            nodes = await fusion_retriever.aretrieve(QueryBundle(query_str=query))
        logger.info("retrieval_complete", num_nodes=len(nodes))
        
        return nodes
    
    def _deduplicate_nodes(self, nodes: List) -> List:
        """
        Remove duplicate nodes by content.
        
        Hybrid search can return overlapping results from vector and BM25.
        """
        unique_nodes = []
        seen_content = set()
        
        for n in nodes:
            full_content = n.node.get_content()
            
            if full_content not in seen_content:
                seen_content.add(full_content)
                unique_nodes.append(n)
        
        logger.info("deduplication_complete", original=len(nodes), unique=len(unique_nodes))
        return unique_nodes
    
    async def _rerank_results(
        self,
        query: str,
        nodes: List,
        top_k: int
    ) -> List:
        """
        Rerank results using semantic similarity model.
        
        Args:
            query: Search query
            nodes: Candidate nodes
            top_k: Number of top results to return
            
        Returns:
            Reranked list of nodes
        """
        if not nodes:
            logger.warning("no_candidates_for_reranking")
            return []
        
        from infrastructure.factories.reranker_factory import RerankerFactory
        from infrastructure.monitoring import record_rag_processing
        
        candidate_texts = [n.node.get_content() for n in nodes]
        
        logger.info("reranking_started", num_candidates=len(candidate_texts), top_k=top_k)
        with record_rag_processing(domain="nse", stage="reranking"):
            reranker_results = await asyncio.to_thread(
                RerankerFactory.predict,
                query,
                candidate_texts,
                top_k=top_k
            )
        logger.info("reranking_complete")
        
        # Reconstruct nodes with new scores
        reranked_nodes = []
        for idx, score in reranker_results:
            original_node = nodes[idx]
            original_node.score = float(score)
            reranked_nodes.append(original_node)
        
        return reranked_nodes
    
    def _format_search_results(
        self,
        query: str,
        nodes: List,
        filters: Optional[MetadataFilters]
    ) -> Dict[str, Any]:
        """Format search results for API response."""
        results = []
        for n in nodes:
            results.append({
                "text": n.node.get_content(),
                "score": n.score,
                "metadata": n.node.metadata
            })
        
        return {
            "query": query,
            "filters": [f.dict() for f in filters.filters] if filters else None,
            "results": results,
            "count": len(results)
        }



    async def close(self):
        """
        Cleanup resources.
        """
        await super().close()

# Singleton instance
rag_service = RagService()

