import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from openai import AsyncOpenAI
# from llama_index.llms.openai import OpenAI # REMOVED: Incompatible with uvloop
# from llama_index.core.llms import ChatMessage # REMOVED

from modules.domains.core.services.base_rag_service import BaseRagService
from modules.domains.nse.services.parsers.nse_parser import NSEEarningsParser
from modules.domains.nse.services.parsers.metadata import NSEDocumentMetadata
from modules.domains.nse.services.retrievers.hybrid_retriever import TenantAwareHybridRetriever

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
        # Specialized LLM for Query Decomposition (Fast & Cheap)
        # Using raw AsyncOpenAI client to avoid LlamaIndex/uvloop conflicts
        import os
        self._router_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_index_name(self) -> str:
        return self._index_name

    def get_parser(self):
        return NSEEarningsParser()

    async def _decompose_query(self, query_text: str) -> Optional[MetadataFilters]:
        """
        Uses LLM to extract metadata filters (Ticker, Year, Scope) from natural language query.
        Example: "Revenue of TCS in FY25" -> {ticker: TCS, fiscal_year: FY25}
        """
        try:
            # reuse NSEDocumentMetadata schema which has the fields we want
            prompt_template_str = (
                "You are an expert financial query parser. Your job is to extract search filters from the user's natural language question.\n"
                "Target Metadata Fields:\n"
                "- ticker: The stock ticker symbol of the company explicitly mentioned (e.g., 'reliance' -> 'RELIANCE', 'tcs' -> 'TCS').\n"
                "- fiscal_year: The Fiscal Year if mentioned (e.g., 'FY25', '2025').\n"
                "- quarter: The Quarter if mentioned (e.g., 'Q2', 'second quarter').\n"
                "- scope: 'Standalone' or 'Consolidated' if strictly mentioned.\n\n"
                "Rules:\n"
                "1. If a company name is mentioned (even in lowercase like 'reliance'), extract its standard ticker (e.g. RELIANCE).\n"
                "2. If no company is mentioned, leave ticker null.\n"
                "3. Do not infer filters that are not in the query.\n\n"
                "User Question: {query_str}\n"
                "Metadata:"
            )
            
            # Executing ASYNC LLM call directly to bypass LLMTextCompletionProgram loop patching issues
            # We instruct the LLM to return JSON and parse it manually.
            
            messages = [
                {"role": "system", "content": prompt_template_str.format(query_str=query_text) + "\n\nReturn the result as a valid JSON object matching the metadata schema."},
                {"role": "user", "content": query_text}
            ]
            
            response = await self._router_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Use Pydantic to validate/parse the JSON string (cleaning markdown block ticks if present)
            clean_content = content.replace("```json", "").replace("```", "").strip()
            output = NSEDocumentMetadata.model_validate_json(clean_content)
            
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
        2. Retrieve (Hybrid + Tenant Isolation + Filters)
        3. Synthesize (TODO: integrate synth, for now returning nodes)
        """
        self._ensure_initialized()
        
        # 1. Decompose Query
        filters = await self._decompose_query(query)
        logger.info(f"DEBUG_RAG: User Query: '{query}'")
        if filters:
             logger.info(f"DEBUG_RAG: Decomposed Filters: {filters.filters}")
        else:
             logger.info("DEBUG_RAG: No filters decomposed (General Query)")
        
        # 2. Initialize Retriever with Filters
        retriever = TenantAwareHybridRetriever(
            embed_model=self.embed_model,
            index_name=self.get_index_name(),
            tenant_id=str(tenant_id),
            filters=filters
        )
        
        # 3. Execute Retrieval
        from llama_index.core.schema import QueryBundle
        nodes = await retriever.aretrieve(QueryBundle(query_str=query))
        
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



# Singleton instance
rag_service = RagService()

