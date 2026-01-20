from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db.session import get_db
from modules.b2b.rbac import require_permission

from modules.domains.b2b.bank_surveillance.services.orchestrator import orchestrator_service
from modules.domains.b2b.bank_surveillance.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse
)

router = APIRouter(prefix="/api/b2b/domain/bank_surveillance", tags=["Surveillance Analysis Engine"])

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_communication(
    request: AnalysisRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("investigations", "read")
):
    """
    Performs comprehensive multi-agent analysis of a communication.
    Identifies intent, policy violations, and evasion tactics.
    """
    # Strict Validation: If metadata contains region, ensure user has access.
    if request.metadata and 'data_region_id' in request.metadata:
        from modules.b2b.rbac.permission_checker import has_permission_with_plugins
        
        region_id = request.metadata['data_region_id']
        
        allowed = await has_permission_with_plugins(
            current_user['id'],
            "investigations", # Resource Type
            "read",
            db,
            role_id=current_user.get('role_id'),
            extra_context={
                "user": current_user,
                "data_region_id": region_id
            }
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized for this region."
            )

    report = await orchestrator_service.investigate_email(
        email_text=request.text,
        email_metadata=request.metadata or {},
        tenant_id=current_user['tenant_id'],
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
