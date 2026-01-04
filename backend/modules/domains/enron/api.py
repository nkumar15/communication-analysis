from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from core.db.session import get_db
from modules.domains.enron.models import EnronEmail
from modules.domains.enron.schemas import EnronEmailResponse
from modules.domains.enron.services.rag import enron_rag_service
from modules.domains.enron.services.orchestrator import orchestrator_service
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

router = APIRouter(prefix="/api/domain/enron", tags=["Enron"])

@router.get("/emails/{email_id}", response_model=EnronEmailResponse)
async def get_email(email_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific email by ID."""
    result = await db.execute(select(EnronEmail).where(EnronEmail.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email

@router.get("/search")
async def search_emails(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """Search emails using RAG (Hybrid/Vector)."""
    # For POC, we use a default tenant_id derived from a fixed string as described in ingestion
    # Ideally, this comes from auth context.
    # We'll use a placeholder tenant for search across all 'enron' data for now.
    # Ingestion used uuid5(NAMESPACE_DNS, username).
    # If we want to search ALL, we might need a way to search across tenants or use a 'master' tenant.
    # For now, let's assume we search a specific known desk/tenant or just use a dummy one if RAG service handles it.
    # EnronRagService.search implementation had TODO for filter.
    # We will pass a dummy UUID for now.
    dummy_tenant_id = uuid.uuid5(uuid.NAMESPACE_DNS, "unknown") 
    
    results = await enron_rag_service.search(query=q, tenant_id=dummy_tenant_id, limit=limit)
    return results

# Investigation API Schemas
class InvestigateEmailRequest(BaseModel):
    email_text: str = Field(..., description="The email content to investigate")
    email_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (sender, recipient, subject, etc.)")
    tenant_id: Optional[uuid.UUID] = Field(default=None, description="Optional tenant ID for multi-tenancy")

class InvestigateEmailResponse(BaseModel):
    """Investigation report returned to the client"""
    timestamp: str
    risk_level: str = Field(description="Overall risk: high, medium, low, unknown")
    requires_action: bool
    summary: str
    intent_verdict: Optional[Dict[str, Any]] = None
    policy_verdict: Optional[Dict[str, Any]] = None
    evasion_verdict: Optional[Dict[str, Any]] = None
    graph_context: Optional[Dict[str, Any]] = None
    tenant_id: Optional[uuid.UUID] = None
    timeline: Optional[List[Dict[str, Any]]] = None
    evidence_pack: Optional[List[str]] = None

@router.post("/investigate", response_model=InvestigateEmailResponse)
async def investigate_email(request: InvestigateEmailRequest, db: AsyncSession = Depends(get_db)):
    """
    Performs comprehensive multi-agent investigation of an email.
    
    Workflow:
    1. Intent Classification (always runs)
    2. If suspicious: Policy Check + Evasion Check (parallel)
    3. Returns unified InvestigationReport
    """
    report = await orchestrator_service.investigate_email(
        email_text=request.email_text,
        email_metadata=request.email_metadata or {},
        tenant_id=request.tenant_id,
        db=db
    )
    
    return InvestigateEmailResponse(
        timestamp=report.timestamp.isoformat(),
        risk_level=report.risk_level,
        requires_action=report.requires_action,
        summary=report.summary,
        intent_verdict=report.intent_verdict,
        policy_verdict=report.policy_verdict,
        evasion_verdict=report.evasion_verdict,
        graph_context=report.graph_context,
        tenant_id=report.tenant_id,
        timeline=report.timeline,
        evidence_pack=report.evidence_pack
    )

# --- Graph Network Analysis Endpoints ---
from modules.domains.enron.services.graph import graph_service
from modules.domains.enron.constants import DEFAULT_TENANT_ID

@router.post("/graph/build")
async def build_graph(db: AsyncSession = Depends(get_db)):
    """Triggers construction of the communication graph from DB."""
    # Using DEFAULT_TENANT_ID for this POC. In real-world, user's tenant.
    G = await graph_service.build_graph(db, tenant_id=DEFAULT_TENANT_ID)
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "density": nx.density(G),
        "message": "Graph built successfully"
    }

@router.get("/graph/summary")
async def get_graph_summary(db: AsyncSession = Depends(get_db)):
    """Returns basic stats about the current graph."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    
    return {
        "nodes": graph_service.graph.number_of_nodes(),
        "edges": graph_service.graph.number_of_edges(),
        "last_updated": graph_service.last_updated,
        "cliques_count": len(graph_service.detect_cliques()),
    }

@router.get("/graph/cliques")
async def get_cliques(min_size: int = 3, db: AsyncSession = Depends(get_db)):
    """Returns a list of suspicious cliques (closed communication loops)."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    return graph_service.detect_cliques(min_size=min_size)

@router.get("/graph/ego/{email}")
async def get_ego_graph(email: str, radius: int = 1, db: AsyncSession = Depends(get_db)):
    """Returns the ego network for a specific email address (for visualization)."""
    if graph_service.graph.number_of_nodes() == 0:
        await graph_service.build_graph(db, DEFAULT_TENANT_ID)
    return graph_service.get_ego_network(email, radius)

import networkx as nx 
