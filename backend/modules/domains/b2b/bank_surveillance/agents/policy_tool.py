from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from modules.domains.b2b.bank_surveillance.services.policy import policy_rag_service

class SearchRegulationsInput(BaseModel):
    query: str = Field(description="The legal concept or keyword to search for (e.g. 'Rule 10b-5', 'Conflict of Interest')")

class SearchRegulationsTool(BaseTool):
    name: str = "search_regulations"
    description: str = "Searches the Enron Regulatory Knowledge Base (SEC Rules, Ethics Code) for relevant laws and policies."
    args_schema: Type[BaseModel] = SearchRegulationsInput

    def _run(self, query: str, **kwargs):
        raise NotImplementedError("Use _arun instead - this tool requires async context")

    async def _arun(self, query: str, run_manager=None, **kwargs):
        # Extract tenant_id from LangChain config if available
        tenant_id = None
        if run_manager and hasattr(run_manager, 'get_config'):
            config = run_manager.get_config()
            if config and "configurable" in config:
                tenant_id = config["configurable"].get("tenant_id")
        
        try:
            # PolicyRagService.search returns { "query": str, "results": [ { "text": ..., "source": ... } ] }
            results = await policy_rag_service.search(query=query, limit=4, tenant_id=tenant_id)
            
            if not results or not results.get("results"):
                return "No relevant regulations found."
                
            formatted = f"Found {len(results['results'])} relevant regulatory excerpts for '{query}':\n\n"
            for i, item in enumerate(results["results"]):
                text = item.get('text', '').strip()
                source = item.get('source', 'Unknown')
                formatted += f"--- DOCUMENT {i+1} ({source}) ---\n{text}\n\n"
            
            return formatted
            
        except Exception as e:
            return f"Error searching regulations: {str(e)}"
