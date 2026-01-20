from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.db.session import get_db

from modules.domains.b2b.bank_surveillance.services.orchestrator import orchestrator_service
from modules.domains.b2b.bank_surveillance.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse
)

router = APIRouter(prefix="/api/b2b/domain/bank_surveillance", tags=["Surveillance Analysis Engine"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_communication(request: AnalysisRequest, db: AsyncSession = Depends(get_db)):
    """
    Performs comprehensive multi-agent analysis of a communication.
    Identifies intent, policy violations, and evasion tactics.
    """
    report = await orchestrator_service.investigate_email(
        email_text=request.text,
        email_metadata=request.metadata or {},
        tenant_id=request.tenant_id,
        db=db
    )
    
    return AnalysisResponse(
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
