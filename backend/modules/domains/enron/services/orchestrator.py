"""
Multi-Agent Orchestrator for Enron Email Investigation

Coordinates Intent, Policy, and Evasion agents to perform comprehensive email analysis.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

# Import all three agents
from modules.domains.enron.agents.intent_agent import intent_agent
from modules.domains.enron.agents.policy_agent import policy_agent
from modules.domains.enron.agents.evasion_agent import evasion_agent

# Investigation Report Schema
class InvestigationReport(BaseModel):
    """Comprehensive investigation report combining all agent verdicts"""
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: Optional[UUID] = None
    email_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Agent Results
    intent_verdict: Optional[Dict[str, Any]] = None
    policy_verdict: Optional[Dict[str, Any]] = None
    evasion_verdict: Optional[Dict[str, Any]] = None
    
    # Summary
    risk_level: str = Field(default="unknown", description="Overall risk: 'high', 'medium', 'low', 'none'")
    requires_action: bool = Field(default=False, description="Whether this case requires human review")
    summary: str = Field(default="", description="Brief summary of findings")

class OrchestratorService:
    """Coordinates multiple agents to investigate emails"""
    
    def __init__(self, tenant_id: UUID = None):
        self.tenant_id = tenant_id
    
    async def investigate_email(
        self, 
        email_text: str, 
        email_metadata: Dict[str, Any] = None,
        tenant_id: UUID = None
    ) -> InvestigationReport:
        """
        Performs comprehensive investigation of an email using all agents.
        
        Workflow:
        1. Intent Classification (always run)
        2. If suspicious: Policy Check + Evasion Check (parallel)
        3. Compile results into unified report
        
        Args:
            email_text: The email content to investigate
            email_metadata: Optional metadata (sender, recipient, date, etc.)
            tenant_id: Optional tenant ID (overrides instance tenant_id)
        
        Returns:
            InvestigationReport with all agent verdicts
        """
        effective_tenant_id = tenant_id or self.tenant_id
        email_metadata = email_metadata or {}
        
        # Step 1: Intent Classification (Triage)
        intent_result = await intent_agent.classify_email(email_text, tenant_id=effective_tenant_id)
        classification = intent_result.get("classification", "").lower()
        
        # Initialize report
        report = InvestigationReport(
            tenant_id=effective_tenant_id,
            email_metadata=email_metadata,
            intent_verdict=intent_result
        )
        
        # Step 2: Conditional Deep Analysis
        if classification in ["fraud/collusion", "evasion attempt"]:
            # Run Policy and Evasion checks in parallel
            import asyncio
            policy_task = policy_agent.analyze_email(email_text, tenant_id=effective_tenant_id)
            evasion_task = evasion_agent.analyze_email(email_text, tenant_id=effective_tenant_id)
            
            policy_result, evasion_result = await asyncio.gather(policy_task, evasion_task)
            
            report.policy_verdict = policy_result
            report.evasion_verdict = evasion_result
            
            # Determine risk level
            is_policy_violation = not policy_result.get("is_compliant", True)
            is_evasion = evasion_result.get("is_evasion", False)
            
            if is_policy_violation and is_evasion:
                report.risk_level = "high"
                report.requires_action = True
                report.summary = f"CRITICAL: Email classified as '{classification}' with policy violation ({policy_result.get('violation_citation')}) AND evasion attempt ({evasion_result.get('evasion_type')})."
            elif is_policy_violation or is_evasion:
                report.risk_level = "high"
                report.requires_action = True
                if is_policy_violation:
                    report.summary = f"HIGH RISK: Policy violation detected - {policy_result.get('violation_citation')}. Classified as '{classification}'."
                else:
                    report.summary = f"HIGH RISK: Evasion attempt detected - {evasion_result.get('evasion_type')}. Classified as '{classification}'."
            else:
                # Classified as suspicious but no violations found
                report.risk_level = "medium"
                report.requires_action = False
                report.summary = f"MEDIUM RISK: Classified as '{classification}' but no specific violations detected. Recommend manual review."
        else:
            # Business as usual
            report.risk_level = "low"
            report.requires_action = False
            report.summary = f"LOW RISK: Email classified as '{classification}'. No further action required."
        
        return report

# Singleton
from modules.domains.enron.constants import DEFAULT_TENANT_ID
orchestrator_service = OrchestratorService(tenant_id=DEFAULT_TENANT_ID)
