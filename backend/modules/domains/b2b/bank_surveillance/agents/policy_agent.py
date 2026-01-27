from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from modules.domains.b2b.bank_surveillance.agents.policy_tool import SearchRegulationsTool
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
        
        system_prompt = """You are a Senior Corporate Compliance Officer at Worldwide Bank. 
Your job is to analyze flagged communications and validate whether they violate company policy or securities law.

You have access to a tool 'search_regulations' to find relevant laws.
ALWAYS use the tool to check for violations if the communication discusses:
- Suspicious off-balance sheet transactions or shell companies
- Intentional document destruction or evasion of recording
- Potential insider trading or market manipulation
- Moving business discussions to personal or unmonitored channels

Analyze the content, query the regulations if needed, and provide a final verdict.
CRITICAL: In your reasoning, you MUST include VERBATIM QUOTES from the relevant regulation text that apply to this violation. 
If the search tool does not return the exact text after 2 attempts, STOP SEARCHING. 
Rely on your internal knowledge to provide the verdict and explicitly state that the citation is based on general knowledge due to missing reference text."""
        
        # New simplified API in LangChain 1.2.0
        self.agent = create_agent(
            model=self.llm, 
            tools=self.tools, 
            system_prompt=system_prompt,
            response_format=ComplianceVerdict
        )

    async def analyze_email(self, email_text: str, tenant_id: UUID = None, likely_risks: list[str] = None, regulatory_context: str = None) -> dict:
        """
        Analyzes an email for compliance violations.
        
        Args:
            email_text: The email content to analyze
            tenant_id: Optional tenant ID for filtering tenant-specific regulations
            likely_risks: Optional list of risk indicators detected by other systems (e.g. "Wash Trading")
            regulatory_context: Specific regulation citation to check against (e.g. "SEC Rule 10b-5")
        """
        # Use provided tenant_id or fall back to instance tenant_id
        effective_tenant_id = tenant_id or self.tenant_id
        
        prompt_content = email_text
        if likely_risks:
            risks_str = ", ".join(likely_risks)
            prompt_content = (
                f"CONTEXT: The monitoring system has flagged this communication for potential: {risks_str}.\n"
            )
            
            if regulatory_context:
                prompt_content += f"RELEVANT REGULATION: {regulatory_context}\n"
                prompt_content += f"Please verify if this constitutes a violation of {regulatory_context} or other regulations related to {risks_str}.\n\n"
            else:
                prompt_content += f"Please verify if this constitutes a violation of regulations related to {risks_str}.\n\n"
            
            prompt_content += f"EMAIL CONTENT:\n{email_text}"
        
        try:
            # Pass tenant_id via config to make it available to tools
            config = {"configurable": {"tenant_id": effective_tenant_id}, "recursion_limit": 15} if effective_tenant_id else {"recursion_limit": 15}
            result = await self.agent.ainvoke({"messages": [("user", prompt_content)]}, config=config)
            
            # LangChain 1.2.0 returns a dict with 'structured_response' key
            if isinstance(result, dict) and "structured_response" in result:
                verdict = result["structured_response"]
                if hasattr(verdict, "dict"):
                    return verdict.dict()
                return verdict
            
            # Fallback for tool-using agents which might return 'output' or other keys
            # If the runnable returns the Pydantic object directly (some chains do)
            if hasattr(result, "dict"):
                 return result.dict()
            
            # If it's a dict but no structured_response, it might be the state dict
            # Check if fields exist directly
            if isinstance(result, dict) and "is_compliant" in result:
                return result

            return result
            
        except Exception as e:
             return {
                "is_compliant": False,
                "violation_citation": "System Error",
                "reasoning": str(e)
            }

# Demo singleton with default tenant
# In production, instantiate PolicyAgent per-request with the user's tenant_id
# Singleton instance removed - instantiate per request
# policy_agent = PolicyAgent(tenant_id=None)
