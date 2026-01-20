from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from uuid import UUID
import os

# Define output schema
class IntentVerdict(BaseModel):
    classification: str = Field(description="Email classification: 'Evasion Attempt', 'Fraud/Collusion', or 'Business as Usual'")
    reasoning: str = Field(description="Detailed explanation of the classification decision")
    confidence: float = Field(description="Confidence score 0.0-1.0")

class IntentAgent:
    def __init__(self, tenant_id: UUID = None):
        # Allow overriding model via env
        model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.tenant_id = tenant_id
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        
        # Validated prompt from 95% accuracy experiment
        system_prompt = """You are an expert fraud investigator for Worldwide Bank. 
Your goal is to identify COMMUNICATIONS that indicate financial fraud, evasion, or collusion.

Classify the message into one of these categories:

1. 'Evasion Attempt': The sender is explicitly trying to move conversation to a non-recorded channel (cell, home, offline) or destroy/hide evidence.
2. 'Fraud/Collusion': The message explicitly discusses suspicious financial mechanisms (off-balance-sheet entities, market manipulation) or illicit deals.
3. 'Business as Usual': Normal corporate communication, personal chatter, scheduling, or generic industry news.

CRITICAL RULES:
- If the message is a generic News Digest or forwarded public article: Label as 'Business as Usual'.
- If the message discusses moving a sensitive deal discussion "offline" or to a "personal line": Label as 'Evasion Attempt'.
- Label suspicious financial coordination between trading desks or with outside parties as 'Fraud/Collusion'.

Analyze the content carefully and provide your classification with reasoning."""
        
        # No tools needed - direct reasoning
        self.agent = create_agent(
            model=self.llm, 
            tools=[],  # No external tools
            system_prompt=system_prompt,
            response_format=IntentVerdict
        )

    async def classify_email(self, email_text: str, tenant_id: UUID = None) -> dict:
        """
        Classifies an email's intent.
        
        Args:
            email_text: The email content to classify
            tenant_id: Optional tenant ID (for consistency with other agents)
        
        Returns:
            IntentVerdict dict with classification, reasoning, and confidence
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
                "classification": "Error",
                "reasoning": str(e),
                "confidence": 0.0
            }

# Demo singleton with default tenant
# Singleton instance removed - instantiate per request
# intent_agent = IntentAgent(tenant_id=None)
