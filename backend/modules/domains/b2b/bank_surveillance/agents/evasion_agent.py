from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from uuid import UUID
import os

# Define output schema
class EvasionVerdict(BaseModel):
    is_evasion: bool = Field(description="True if the email shows attempt to evade surveillance, False otherwise")
    evasion_type: str = Field(description="Type of evasion: 'channel_switch' (moving to phone/personal email), 'evidence_destruction' (delete/shred), 'none', or 'ambiguous'")
    evidence: str = Field(description="The specific phrases or sentences that indicate evasion behavior")
    confidence: float = Field(description="Confidence score 0.0-1.0")

class EvasionAgent:
    def __init__(self, tenant_id: UUID = None):
        # Allow overriding model via env
        model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.tenant_id = tenant_id
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        
        system_prompt = """You are a Corporate Surveillance Analyst specializing in detecting evasion tactics.

Your job is to identify if an employee is attempting to EVADE compliance monitoring by:
1. **Channel Switching**: Suggesting to move the conversation to unmonitored channels
   - Examples: "call my cell", "use my personal email", "let's discuss this offline", "talk in person"
2. **Evidence Destruction**: Requesting deletion or destruction of records
   - Examples: "delete this email", "shred the documents", "don't put this in writing"

CRITICAL RULES:
- Normal scheduling ("let's meet at 3pm") is NOT evasion
- Casual references to phones ("my cell is 555-1234 if you need me") are NOT evasion
- Context matters: "call me on my cell about the project deadline" is BENIGN
- But "call me on my cell about the off-balance sheet transaction" is SUSPICIOUS

Analyze the email and determine if there is genuine evasion intent."""
        
        # No tools needed - direct reasoning
        self.agent = create_agent(
            model=self.llm, 
            tools=[],  # No external tools
            system_prompt=system_prompt,
            response_format=EvasionVerdict
        )

    async def analyze_email(self, email_text: str, tenant_id: UUID = None) -> dict:
        """
        Analyzes an email for evasion attempts.
        
        Args:
            email_text: The email content to analyze
            tenant_id: Optional tenant ID (for consistency with other agents)
        """
        try:
            result = await self.agent.ainvoke({"messages": [("user", email_text)]})
            
            # LangChain 1.2.0 returns a dict with 'structured_response' key
            if isinstance(result, dict) and "structured_response" in result:
                verdict = result["structured_response"]
                if hasattr(verdict, "dict"):
                    return verdict.dict()
                return verdict
            
            # Fallback: if it's already a pydantic model
            if hasattr(result, "dict"):
                return result.dict()
                
            return result
            
        except Exception as e:
            return {
                "is_evasion": False,
                "evasion_type": "error",
                "evidence": str(e),
                "confidence": 0.0
            }

# Demo singleton with default tenant
from modules.domains.b2b.bank_surveillance.constants import DEFAULT_TENANT_ID
evasion_agent = EvasionAgent(tenant_id=DEFAULT_TENANT_ID)
