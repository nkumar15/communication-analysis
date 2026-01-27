import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.db.session import get_db
from modules.b2b.rbac import require_permission

from modules.domains.b2b.bank_surveillance.services.orchestrator import orchestrator_service
from modules.domains.b2b.bank_surveillance.services.alert_service import alert_service
from modules.domains.b2b.bank_surveillance.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AlertInvestigationRequest
)

router = APIRouter(prefix="", tags=["Surveillance Analysis Engine"])

@router.post("/alerts/{alert_id}/investigate", response_model=AnalysisResponse)
async def investigate_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = require_permission("investigations", "read")
):
    """
    Triggers a multi-agent AI investigation for a specific Alert.
    Fetches the underlying communication and coordinates agents.
    """
    tenant_id = current_user['tenant_id']
    
    # 1. Fetch Alert to get context
    # 1. Fetch Alert to get context
    alert = await alert_service.get_alert(db, alert_id, tenant_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if not alert.communication:
        raise HTTPException(status_code=400, detail="Alert has no linked communication for analysis")

    # 1.5 Fetch Regulatory Context from Triggered Controls
    from sqlalchemy import select
    from modules.domains.b2b.bank_surveillance.models.surveillance_control import SurveillanceControl
    from modules.domains.b2b.bank_surveillance.models.incident import Incident

    # Find the controls that triggered this alert via incidents
    stmt = select(SurveillanceControl).join(Incident, Incident.control_id == SurveillanceControl.id).where(Incident.alert_id == alert_id)
    controls_res = await db.execute(stmt)
    controls = controls_res.scalars().all()

    risk_indicators = [c.risk_indicator for c in controls if c.risk_indicator]
    regulations = [c.regulatory_reference_text for c in controls if c.regulatory_reference_text]

    # Deduplicate
    risk_indicators = list(set(risk_indicators))
    regulatory_context = "; ".join(list(set(regulations)))

    # 2. Run Multi-Agent Orchestrator
    report = await orchestrator_service.investigate_email(
        email_text=alert.communication.content or "",
        email_metadata={
            "sender": alert.communication.sender,
            "subject": alert.communication.subject,
            "date": alert.communication.timestamp.isoformat() if alert.communication.timestamp else None,
            "alert_id": str(alert_id),
            "risk_indicators": risk_indicators,
            "regulatory_context": regulatory_context
        },
        tenant_id=tenant_id,
        db=db
    )

    # 3. Persist Report to Alert Metadata for Caching
    analysis_data = {
        "timestamp": report.timestamp.isoformat(),
        "risk_level": report.risk_level,
        "requires_action": report.requires_action,
        "summary": report.summary,
        "intent_verdict": report.intent_verdict,
        "policy_verdict": report.policy_verdict,
        "evasion_verdict": report.evasion_verdict,
        "graph_context": report.graph_context,
        "timeline": report.timeline,
        "evidence_pack": report.evidence_pack
    }
    
    # Ensure metadata exists and update it
    current_metadata = alert.metadata_ or {}
    current_metadata["ai_analysis"] = analysis_data
    alert.metadata_ = current_metadata
    
    db.add(alert)
    await db.commit()
    
    return AnalysisResponse(
        tenant_id=report.tenant_id,
        **analysis_data
    )

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_communication_raw(
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
