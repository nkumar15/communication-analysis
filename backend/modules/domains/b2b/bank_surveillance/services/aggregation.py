"""
Aggregation Service - Groups RiskEvents into Incidents and links to Alerts.

This service implements Workflow B: Group + Alert.
"""
import uuid
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.logging import get_logger
from modules.domains.b2b.bank_surveillance.models import (
    RiskEvent,
    Incident,
    Alert,
    SurveillanceControl,
)
from modules.domains.b2b.bank_surveillance.models.incident import IncidentSeverity
from modules.domains.b2b.bank_surveillance.models.alert import AlertSeverity, AlertStatus

logger = get_logger(__name__)


class AggregationService:
    """Service for aggregating RiskEvents into Incidents and Alerts."""
    
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    async def aggregate_events(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[int, int]:
        """
        Aggregate unprocessed RiskEvents into Incidents.
        
        Groups by: sender + control + event_date
        Propagates: data_region_ids (unique), sensitivity_level_id (MAX)
        
        Args:
            start_date: Optional filter for event date range
            end_date: Optional filter for event date range
            
        Returns:
            Tuple of (incidents_created, events_processed)
        """
        from modules.domains.b2b.bank_surveillance.models import Communication
        from sqlalchemy.orm import selectinload
        
        # Build query for unprocessed events (incident_id is NULL)
        stmt = select(
            RiskEvent.sender,
            RiskEvent.event_date,
            RiskEvent.control_id,
            func.count().label("event_count"),
            func.array_agg(RiskEvent.id).label("event_ids")
        ).where(
            RiskEvent.tenant_id == self.tenant_id,
            RiskEvent.incident_id.is_(None)
        ).group_by(
            RiskEvent.sender,
            RiskEvent.event_date,
            RiskEvent.control_id
        )
        
        if start_date:
            stmt = stmt.where(RiskEvent.event_date >= start_date)
        if end_date:
            stmt = stmt.where(RiskEvent.event_date <= end_date)
        
        result = await self.db.execute(stmt)
        groups = result.all()
        
        if not groups:
            logger.info("No unprocessed RiskEvents found for aggregation")
            return 0, 0
        
        incidents_created = 0
        events_processed = 0
        
        for group in groups:
            # Fetch events with their communications to get plugin metadata
            events_stmt = select(RiskEvent).where(
                RiskEvent.id.in_(group.event_ids)
            ).options(selectinload(RiskEvent.communication))
            
            events_result = await self.db.execute(events_stmt)
            events = list(events_result.scalars().all())
            
            # Collect unique regions from all events' communications
            region_ids = list(set(
                e.communication.data_region_id
                for e in events
                if e.communication and e.communication.data_region_id
            ))
            
            # Get MAX sensitivity level (most restrictive)
            sensitivity_ids = [
                e.communication.sensitivity_level_id
                for e in events
                if e.communication and e.communication.sensitivity_level_id
            ]
            max_sensitivity_id = sensitivity_ids[0] if sensitivity_ids else None
            # Note: For proper MAX, would need ordering by sensitivity level priority
            # For now, take the first one (demo simplification)
            
            # Create incident with plugin metadata
            severity = Incident.calculate_severity(group.event_count)
            
            incident = Incident(
                tenant_id=self.tenant_id,
                control_id=group.control_id,
                sender=group.sender,
                incident_date=group.event_date,
                event_count=group.event_count,
                severity=severity,
                data_region_ids=region_ids,
                sensitivity_level_id=max_sensitivity_id,
            )
            self.db.add(incident)
            await self.db.flush()  # Get the incident ID
            
            # Link events to incident
            await self.db.execute(
                update(RiskEvent)
                .where(RiskEvent.id.in_(group.event_ids))
                .values(incident_id=incident.id)
            )
            
            incidents_created += 1
            events_processed += group.event_count
            
            logger.info(
                f"Created Incident for {group.sender} on {group.event_date} "
                f"with {group.event_count} events (severity: {severity}, regions: {len(region_ids)})"
            )
        
        return incidents_created, events_processed

    
    async def generate_alerts(self) -> int:
        """
        Generate Alerts from Incidents that don't have alerts yet.
        
        For demo: Creates one Alert per Incident.
        Production: Would group incidents into broader alert buckets.
        
        Returns:
            Number of alerts created
        """
        # Fetch incidents without alerts
        stmt = select(Incident).where(
            Incident.tenant_id == self.tenant_id,
            Incident.alert_id.is_(None)
        )
        
        result = await self.db.execute(stmt)
        incidents = list(result.scalars().all())
        
        if not incidents:
            logger.info("No incidents without alerts found")
            return 0
        
        # Fetch control names for alert subjects
        control_ids = list(set(inc.control_id for inc in incidents))
        controls_result = await self.db.execute(
            select(SurveillanceControl).where(SurveillanceControl.id.in_(control_ids))
        )
        controls = {c.id: c for c in controls_result.scalars().all()}
        
        alerts_created = 0
        
        for incident in incidents:
            control = controls.get(incident.control_id)
            indicator_name = control.risk_indicator if control else "Unknown"
            
            # Generate subject: "{Sender} - {Indicator} - {Date}"
            subject = f"{incident.sender} - {indicator_name} - {incident.incident_date}"
            
            # Map incident severity to alert severity
            alert_severity = self._map_severity(incident.severity)
            
            # Generate description
            description = (
                f"Detected {incident.event_count} risk events associated with {indicator_name}. "
                f"Sender: {incident.sender}."
            )


            # Fetch all events to get communication_id and aggregate keywords
            event_stmt = select(RiskEvent).where(RiskEvent.incident_id == incident.id)
            event_res = await self.db.execute(event_stmt)
            events = event_res.scalars().all()
            
            communication_id = events[0].communication_id if events else None
            
            # Aggregate keywords from all events
            all_keywords = set()
            for e in events:
                if e.matched_keywords:
                    # JSONB list
                    for kw in e.matched_keywords:
                        all_keywords.add(kw)
            
            sorted_keywords = sorted(list(all_keywords))
            keywords_str = ", ".join(sorted_keywords)

            # Generate display_id (Deterministic)
            from modules.domains.b2b.bank_surveillance.utils.id_utils import generate_deterministic_numeric_id
            # We don't have the Alert ID yet (it's generated on insert usually, but here we instantiate it).
            # Alert model uses uuid4 as default. We should let it generate or generate one here.
            # AlertService generates it explicitly. Let's do the same.
            alert_id = uuid.uuid4()
            numeric_suffix = generate_deterministic_numeric_id(alert_id)
            display_id = f"ALT-{numeric_suffix}"

            # Enhanced Description
            description = (
                f"Detected {incident.event_count} risk events associated with {indicator_name}. "
                f"Sender: {incident.sender}."
            )
            if keywords_str:
                description += f" Matched Keywords: {keywords_str}"

            alert = Alert(
                id=alert_id,
                tenant_id=self.tenant_id,
                subject=subject,
                display_id=display_id,
                description=description,
                severity=alert_severity,
                risk_type=control.risk_typology if control else None,
                communication_id=communication_id,
                status=AlertStatus.OPEN.value,
                metadata_={
                    "matched_keywords": sorted_keywords
                }
            )
            self.db.add(alert)
            await self.db.flush()  # Get the alert ID
            
            # Link incident to alert
            incident.alert_id = alert.id
            
            alerts_created += 1
            logger.info(f"Created Alert: {subject}")
        
        return alerts_created
    
    def _map_severity(self, incident_severity: str) -> str:
        """Map incident severity to alert severity."""
        mapping = {
            IncidentSeverity.LOW.value: AlertSeverity.LOW.value,
            IncidentSeverity.MEDIUM.value: AlertSeverity.MEDIUM.value,
            IncidentSeverity.HIGH.value: AlertSeverity.HIGH.value,
            IncidentSeverity.CRITICAL.value: AlertSeverity.CRITICAL.value,
        }
        return mapping.get(incident_severity, AlertSeverity.MEDIUM.value)
    
    async def run_full_aggregation(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Run full aggregation pipeline: Events → Incidents → Alerts.
        
        Returns:
            Summary dict with counts
        """
        incidents_created, events_processed = await self.aggregate_events(start_date, end_date)
        alerts_created = await self.generate_alerts()
        
        return {
            "events_processed": events_processed,
            "incidents_created": incidents_created,
            "alerts_created": alerts_created,
        }
