import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

# from llama_index.llms.openai import OpenAI # REMOVED: Incompatible with uvloop
# from llama_index.core.llms import ChatMessage # REMOVED

from modules.domains.core.services.base_rag_service import BaseRagService
from modules.domains.nse.services.parsers.nse_parser import NSEEarningsParser
from modules.domains.nse.services.parsers.metadata import NSEDocumentMetadata


logger = logging.getLogger(__name__)

class RagService(BaseRagService):
    """
    NSE Domain Specific RAG Service.
    Extends BaseRagService to provide NSE-specific parser and configuration.
    Now includes 'Query Understanding' layer to extract metadata filters.
    """
    
    def __init__(self, index_name: str = "nse_rag_documents"):
        super().__init__()
        self._index_name = index_name

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
            
            # Use the text of the first document/page
            first_page_text = documents[0].text
            if len(first_page_text) < 100:
                logger.warning(f"[MetadataEnrichment] Text too short length: {len(first_page_text)}")
            
            extractor = MetadataExtractor()
            # Run extraction (it's synchronous for now in the extractor class, but wrapped in async hook)
            # Ideally MetadataExtractor should be async, but for now we run it directly.
            # Depending on LLM implementation it might block, but we are in a thread pool in rag_tasks so it's acceptable.
            metadata_model = extractor.extract(first_page_text)
            
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

    async def search(self, query: str, tenant_id: UUID, **kwargs) -> Dict[str, Any]:
        """
        NSE Specific Search Implementation:
        1. Decompose Query -> Filters
        2. Retrieve (QueryFusionRetriever: Vector + BM25)
        3. Return results
        """
        self._ensure_initialized()
        
        # 1. Decompose Query
        filters = await self._decompose_query(query)
        logger.info(f"DEBUG_RAG: User Query: '{query}'")
        if filters:
             logger.info(f"DEBUG_RAG: Decomposed Filters: {filters.filters}")
        else:
             logger.info("DEBUG_RAG: No filters decomposed (General Query)")
        
        # 2. Setup Retrievers
        try:
            from llama_index.core.retrievers import QueryFusionRetriever
            from llama_index.core import VectorStoreIndex
            from modules.domains.nse.services.retrievers.es_bm25_retriever import ElasticsearchBM25Retriever
            from llama_index.core.retrievers import QueryFusionRetriever
            
            # A. Vector Retriever (Standard LlamaIndex)
            # We need to create an index view first from the vector store
            index = VectorStoreIndex.from_vector_store(self.vector_store, embed_model=self.embed_model)
            
            vector_retriever = index.as_retriever(
                filters=filters,
                similarity_top_k=50 # Retrieve candidates for fusion
            )
            
            # B. BM25 Retriever (Custom ES)
            bm25_retriever = ElasticsearchBM25Retriever(
                index_name=self.get_index_name(),
                tenant_id=str(tenant_id),
                filters=filters,
                top_k=50 
            )
            
            # C. Query Fusion
            from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
            fusion_retriever = QueryFusionRetriever(
                [vector_retriever, bm25_retriever],
                retriever_weights=[0.5, 0.5], # RRF ignores weights usually, but good to have
                similarity_top_k=10, # Final Top K
                num_queries=1, # No query generation extension, just single query fusion
                mode=FUSION_MODES.RECIPROCAL_RANK,
                use_async=True
            )
            
            # 3. Execute Retrieval
            from llama_index.core.schema import QueryBundle
            nodes = await fusion_retriever.aretrieve(QueryBundle(query_str=query))
            
            # Format results
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
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise e



    async def close(self):
        """
        Cleanup resources.
        """
        await super().close()

# Singleton instance
rag_service = RagService()

