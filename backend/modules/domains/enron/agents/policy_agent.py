from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from modules.domains.enron.agents.policy_tool import SearchRegulationsTool
from pydantic import BaseModel, Field
from uuid import UUID
import os

# Define output schema
class ComplianceVerdict(BaseModel):
    is_compliant: bool = Field(description="True if the email follows all policies, False if it violates any.")
    violation_citation: str = Field(description="Name of the specific law or policy violated (e.g. 'SEC Rule 10b-5', 'Code of Ethics Principle 2'), or 'None'.")
    reasoning: str = Field(description="Detailed legal explanation citing the email text and the regulation.")

class PolicyAgent:
    def __init__(self, tenant_id: UUID = None):
        # Allow overriding model via env
        model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.tenant_id = tenant_id  # Store for passing to tools
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.tools = [SearchRegulationsTool()]
        
        system_prompt = """You are a Senior Corporate Compliance Officer at Enron. 
Your job is to analyze flagged emails and validate whether they violate company policy or securities law.

You have access to a tool 'search_regulations' to find relevant laws.
ALWAYS use the tool to check for violations if the email discusses:
- Off-balance sheet partnerships (LJM, Raptor, Chewco)
- Destroying documents
- Insider trading concepts
- Moving to personal channels

Analyze the email, query the regulations if needed, and provide a final verdict."""
        
        # New simplified API in LangChain 1.2.0
        self.agent = create_agent(
            model=self.llm, 
            tools=self.tools, 
            system_prompt=system_prompt,
            response_format=ComplianceVerdict
        )

    async def analyze_email(self, email_text: str, tenant_id: UUID = None) -> dict:
        """
        Analyzes an email for compliance violations.
        
        Args:
            email_text: The email content to analyze
            tenant_id: Optional tenant ID for filtering tenant-specific regulations
        """
        # Use provided tenant_id or fall back to instance tenant_id
        effective_tenant_id = tenant_id or self.tenant_id
        
        try:
            # Pass tenant_id via config to make it available to tools
            config = {"configurable": {"tenant_id": effective_tenant_id}} if effective_tenant_id else {}
            result = await self.agent.ainvoke({"messages": [("user", email_text)]}, config=config)
            
            # The result should be the parsed pydantic object if response_format is used
            # Or it might be in result['output'] or something similar.
            # Usually create_agent returns the output directly or a state dict.
            # If it returns a state dict, look for 'output' or the response format key.
            
            # Let's inspect the result in the test script. 
            # For now, return dict(result) if it's a model, or result if dict.
            if hasattr(result, "dict"):
                 return result.dict()
            return result
            
        except Exception as e:
             return {
                "is_compliant": False,
                "violation_citation": "System Error",
                "reasoning": str(e)
            }

# Demo singleton with default tenant
# In production, instantiate PolicyAgent per-request with the user's tenant_id
from modules.domains.enron.constants import DEFAULT_TENANT_ID
policy_agent = PolicyAgent(tenant_id=DEFAULT_TENANT_ID)
