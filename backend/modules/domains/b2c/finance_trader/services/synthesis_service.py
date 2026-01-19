"""
Synthesis Service

Handles answer generation from retrieved context.
Extracted from router to improve testability and maintainability.
"""
from typing import List, Dict, Any

from infrastructure.logging import get_logger
from infrastructure.monitoring import record_rag_processing
from infrastructure.factories.llm_factory import LLMFactory
from modules.domains.b2c.finance_trader.exceptions import SynthesisError

logger = get_logger(__name__)


class SynthesisService:
    """Service for generating answers from retrieved context."""
    
    async def synthesize_answer(
        self,
        query: str,
        results: List[Dict[str, Any]],
        domain: str = "nse"
    ) -> str:
        """
        Generate answer from search results using LLM.
        
        Args:
            query: User's question
            results: List of search results with text and metadata
            domain: Domain name for monitoring
            
        Returns:
            Generated answer string
            
        Raises:
            SynthesisError: If synthesis fails
        """
        if not results:
            return "I could not find enough relevant information to answer your question."
        
        try:
            context_str = self._build_context(results)
            prompt = self._build_prompt(query, context_str)
            
            with record_rag_processing(domain=domain, stage="synthesis"):
                llm = LLMFactory.get_llm()
                response = await llm.acomplete(prompt)
                answer = response.text
            
            logger.info(
                "synthesis_complete",
                query_length=len(query),
                context_chunks=len(results),
                answer_length=len(answer)
            )
            
            return answer
            
        except Exception as e:
            logger.error(
                "synthesis_failed",
                query=query,
                num_results=len(results),
                error=str(e),
                exc_info=True
            )
            raise SynthesisError(f"Failed to generate answer: {str(e)}") from e
    
    def _build_context(self, results: List[Dict[str, Any]]) -> str:
        """
        Build enriched context string from search results.
        
        Includes metadata like fiscal year and quarter for better context.
        """
        context_parts = []
        
        for r in results:
            metadata = r.get('metadata', {})
            source = metadata.get('source', 'Unknown')
            fiscal_year = metadata.get('fiscal_year', 'N/A')
            quarter = metadata.get('quarter', '')
            
            # Format: Source (FY25 Q2)\nContent: ...
            source_info = f"Source: {source} "
            if fiscal_year != 'N/A':
                source_info += f"({fiscal_year}"
                if quarter:
                    source_info += f" {quarter}"
                source_info += ")"
            
            context_parts.append(
                f"{source_info}\n"
                f"Content: {r.get('text', '')}"
            )
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context_str: str) -> str:
        """
        Build synthesis prompt with guidelines for the LLM.
        
        Emphasizes conciseness and accuracy, avoiding markdown tables.
        """
        return (
            "You are an expert financial analyst. Your goal is to answer the user's question concisely using the provided context.\n\n"
            "**Guidelines:**\n"
            "1. **Conciseness**: Be extremely direct. Limit answer to 2-3 sentences.\n"
            "2. **NO Markdown Tables**: The text provided contains tables. Do NOT re-generate them. The user can see the source tables.\n"
            "3. **Format**: Use bullet points for key figures only.\n"
            "4. **Accuracy**: Use ONLY the provided context.\n"
            "5. **Citations**: Inline the Fiscal Year/Quarter (e.g. [FY25 Q2]) where relevant.\n\n"
            f"**Context**:\n{context_str}\n\n"
            f"**Question**: {query}\n\n"
            "**Answer**:"
        )


# Singleton instance
synthesis_service = SynthesisService()
