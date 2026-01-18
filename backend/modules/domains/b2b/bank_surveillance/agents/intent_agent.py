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
        system_prompt = """You are an expert fraud investigator analyzing the Enron email corpus. 
Your goal is to identify EMAILS WRITTEN BY EMPLOYEES that indicate fraud, evasion, or collusion.

Classify the email into one of these categories:

1. 'Evasion Attempt': The sender is explicitly trying to move conversation to a non-recorded channel (cell, home, offline) or destroy evidence ("shred", "delete").
2. 'Fraud/Collusion': The email explicitly discusses known fraud entities (LJM, Raptor, Chewco, JEDI) or suspicious mechanisms (SPEs, off-balance-sheet) IN A BUSINESS CONTEXT.
3. 'Business as Usual': Normal corporate communication, personal chatter, scheduling, OR publicly available NEWSLETTERS/ARTICLES.

CRITICAL RULES:
- If the email is a News Digest, Newsletter, or forwarded Press/Media article: Label as 'Business as Usual'.
- If the email contains 'LJM', 'Raptor', 'Chewco' and is an internal discussion: Label as 'Fraud/Collusion'.
- If the email says "call my cell" or "take offline" in the context of a sensitive deal: Label as 'Evasion Attempt'.

Analyze the email carefully and provide your classification with reasoning."""
        
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
from modules.domains.b2b.bank_surveillance.constants import DEFAULT_TENANT_ID
intent_agent = IntentAgent(tenant_id=DEFAULT_TENANT_ID)
