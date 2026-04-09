"""
Detection Service - Keyword/Regex detection against messages.

This service executes active SurveillanceControls against Communications 
to generate RiskEvent records.
"""
import re
import uuid
from datetime import date
from typing import List, Dict, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.logging import get_logger
from modules.domains.b2b.bank_surveillance.models import (
    Communication,
    SurveillanceControl,
    RiskEvent,
)

logger = get_logger(__name__)


class DetectionService:
    """Service for detecting risk signals in communications."""
    
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    async def get_active_controls(self) -> List[SurveillanceControl]:
        """Fetch all active surveillance controls for the tenant."""
        stmt = select(SurveillanceControl).where(
            SurveillanceControl.tenant_id == self.tenant_id,
            SurveillanceControl.status == "Active"
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def analyze_communication(
        self, 
        communication: Communication,
        controls: Optional[List[SurveillanceControl]] = None
    ) -> List[RiskEvent]:
        """
        Analyze a single communication against all active controls.
        
        Args:
            communication: The communication to analyze
            controls: Optional list of controls to use (fetches if not provided)
            
        Returns:
            List of RiskEvent records created
        """
        # --- Noise Reduction: Excluded Senders ---
        EXCLUDED_SENDERS = {
            "403095.167547968.1@news.forbesdigital.com",
            "398026.167547968.1@news.forbesdigital.com",
            "no.address@enron.com",
            "newsletter@winecommune.com"
        }
        
        if communication.sender in EXCLUDED_SENDERS:
            logger.info(f"Skipping risk detection for excluded sender: {communication.sender}")
            communication.analyzed = True
            return []
        # -----------------------------------------

        if controls is None:
            controls = await self.get_active_controls()
        
        events_created = []
        
        # Fetch content from ES if not in DB (Storage Refactor)
        content_body = communication.content
        if not content_body and communication.es_document_id:
            try:
                from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
                content_body = await communication_rag_service.get_content_by_id(communication.es_document_id)
            except Exception as e:
                logger.error(f"Failed to fetch content from ES for {communication.id}: {e}")
        
        content_body = content_body or ""

        for control in controls:
            match_result = self._match_control(communication, control, content_body)
            if match_result:
                # Check for existing event (idempotency)
                existing = await self.db.execute(
                    select(RiskEvent).where(
                        RiskEvent.communication_id == communication.id,
                        RiskEvent.control_id == control.id
                    )
                )
                if existing.scalar_one_or_none():
                    continue  # Skip duplicate
                
                event = RiskEvent(
                    tenant_id=self.tenant_id,
                    communication_id=communication.id,
                    control_id=control.id,
                    sender=communication.sender,
                    event_date=communication.timestamp.date() if communication.timestamp else date.today(),
                    match_type=match_result["match_type"],
                    matched_keywords=match_result["matched_keywords"],
                    matched_snippet=match_result.get("snippet"),
                    match_score=match_result.get("score", 1.0),
                )
                self.db.add(event)
                events_created.append(event)
                
                logger.info(
                    f"Created RiskEvent for communication {communication.id} "
                    f"matching control {control.risk_indicator}"
                )
        
        # Mark communication as analyzed
        communication.analyzed = True
        
        return events_created
    
    def _match_control(
        self, 
        communication: Communication, 
        control: SurveillanceControl,
        content: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a communication matches a control's detection methods.
        
        Returns match result dict or None if no match.
        """
        detection_methods = control.detection_methods or []
        
        # Use provided content or fallback to DB
        content_text = (content or communication.content or "").lower()
        subject = (communication.subject or "").lower()
        full_text = f"{subject} {content_text}"
        
        for method in detection_methods:
            method_type = method.get("type", "keyword")
            
            if method_type == "keyword":
                keywords = method.get("keywords", [])
                matched = [kw for kw in keywords if kw.lower() in full_text]
                if matched:
                    # Extract snippet around first match
                    snippet = self._extract_snippet(full_text, matched[0])
                    return {
                        "match_type": "keyword",
                        "matched_keywords": matched,
                        "snippet": snippet,
                        "score": len(matched) / len(keywords) if keywords else 1.0
                    }
            
            elif method_type == "regex":
                patterns = method.get("patterns", [])
                for pattern in patterns:
                    try:
                        match = re.search(pattern, full_text, re.IGNORECASE)
                        if match:
                            return {
                                "match_type": "regex",
                                "matched_keywords": [match.group()],
                                "snippet": self._extract_snippet(full_text, match.group()),
                                "score": 1.0
                            }
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return None
    
    def _extract_snippet(self, text: str, match: str, context_chars: int = 100) -> str:
        """Extract a snippet of text around a match."""
        match_lower = match.lower()
        text_lower = text.lower()
        
        pos = text_lower.find(match_lower)
        if pos == -1:
            return ""
        
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(match) + context_chars)
        
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    async def analyze_unprocessed(self, limit: int = 100) -> int:
        """
        Analyze all unprocessed communications for the tenant.
        
        Args:
            limit: Max number of communications to process
            
        Returns:
            Number of RiskEvents created
        """
        # Fetch unanalyzed communications
        stmt = select(Communication).where(
            Communication.tenant_id == self.tenant_id,
            Communication.analyzed == False  # noqa: E712
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        communications = list(result.scalars().all())
        
        if not communications:
            logger.info("No unprocessed communications found")
            return 0
        
        # Fetch controls once
        controls = await self.get_active_controls()
        if not controls:
            logger.warning("No active surveillance controls found")
            return 0
        
        # Analyze each communication
        total_events = 0
        for comm in communications:
            events = await self.analyze_communication(comm, controls)
            total_events += len(events)
        
        logger.info(f"Analyzed {len(communications)} communications, created {total_events} RiskEvents")
        return total_events
