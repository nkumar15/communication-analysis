from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

class InvestigateRequest(BaseModel):
    text: str = Field(..., description="The content to investigate")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (sender, recipient, subject, etc.)")
    tenant_id: Optional[uuid.UUID] = Field(default=None, description="Optional tenant ID for multi-tenancy")

class InvestigateResponse(BaseModel):
    """Investigation report returned to the client"""
    timestamp: str
    risk_level: str
    requires_action: bool
    summary: str
    intent_verdict: Optional[Dict[str, Any]] = None
    policy_verdict: Optional[Dict[str, Any]] = None
    evasion_verdict: Optional[Dict[str, Any]] = None
    graph_context: Optional[Dict[str, Any]] = None
    tenant_id: Optional[uuid.UUID] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    evidence_pack: Optional[List[str]] = None
