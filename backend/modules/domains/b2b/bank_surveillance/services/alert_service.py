from uuid import UUID, uuid4
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func
from sqlalchemy.orm import selectinload

from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus, AlertSeverity
from modules.domains.b2b.bank_surveillance.models.communication import Communication
from modules.domains.b2b.bank_surveillance.models.risk_event import RiskEvent
from modules.domains.b2b.bank_surveillance.models.surveillance_control import SurveillanceControl
from modules.b2b.models.geographic_region import GeographicRegion
from modules.domains.b2b.bank_surveillance.schemas.alert import AlertCreate, AlertUpdate, AlertFilter, AlertStats, ThreadMessage

class AlertService:
    async def create_alert(self, db: AsyncSession, alert_in: AlertCreate) -> Alert:
        """Create a new alert"""
        db_alert = Alert(
            id=uuid4(), # Generate ID first to derive deterministic display_id
            tenant_id=alert_in.tenant_id,
            communication_id=alert_in.communication_id,
            risk_type=alert_in.risk_type.value,
            severity=alert_in.severity.value,
            status=alert_in.status.value,
            assigned_to=alert_in.assigned_to,
            description=alert_in.description,
            metadata_=alert_in.metadata_,
            detected_at=alert_in.detected_at or datetime.utcnow()
        )
        
        # 1. Derive deterministic numeric ID from UUID
        from modules.domains.b2b.bank_surveillance.utils.id_utils import generate_deterministic_numeric_id
        numeric_suffix = generate_deterministic_numeric_id(db_alert.id)
        db_alert.display_id = f"ALT-{numeric_suffix}"
        
        db.add(db_alert)
        await db.flush()
        await db.refresh(db_alert)
        return db_alert

    async def get_alert(self, db: AsyncSession, alert_id: UUID, tenant_id: UUID) -> Optional[Alert]:
        """Get alert by ID and tenant with full conversation thread context."""
        stmt = select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        ).options(
            selectinload(Alert.communication).selectinload(Communication.region),
            selectinload(Alert.assignee)
        )
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        
        if not alert:
            return None
            
        # Set region name if available
        if alert.communication and alert.communication.region:
            alert.region = alert.communication.region.name
            
        # --- Thread Reconstruction ---
        # 1. Fetch the primary communication
        if alert.communication_id:
            comm_stmt = select(Communication).where(Communication.id == alert.communication_id)
            res = await db.execute(comm_stmt)
            primary_comm = res.scalar_one_or_none()
            
            if primary_comm:
                # 2. Fetch all related communications (same thread OR same sender/day)
                thread_stmt = select(Communication).where(Communication.tenant_id == tenant_id)
                
                if primary_comm.thread_id:
                    thread_stmt = thread_stmt.where(Communication.thread_id == primary_comm.thread_id)
                else:
                    # Fallback: All communications for this sender on the same day
                    start_of_day = primary_comm.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    from datetime import timedelta
                    end_of_day = start_of_day + timedelta(days=1)
                    thread_stmt = thread_stmt.where(
                        Communication.sender == primary_comm.sender,
                        Communication.timestamp >= start_of_day,
                        Communication.timestamp < end_of_day
                    )
                
                thread_stmt = thread_stmt.order_by(Communication.timestamp.asc())
                res = await db.execute(thread_stmt)
                thread_comms = res.scalars().all()
                
                # 3. Fetch RiskEvents for these communications to mark "triggers"
                comm_ids = [c.id for c in thread_comms]
                events_stmt = select(RiskEvent).where(
                    RiskEvent.communication_id.in_(comm_ids)
                ).options(selectinload(RiskEvent.control))
                
                res = await db.execute(events_stmt)
                events = res.scalars().all()
                
                # Group indicators and keywords by communication_id (using string keys for robust UUID matching)
                comms_risk_info = {}
                comms_matched_keywords = {}
                for e in events:
                    cid_str = str(e.communication_id)
                    if cid_str not in comms_risk_info:
                        comms_risk_info[cid_str] = []
                        comms_matched_keywords[cid_str] = []
                        
                    indicator = e.control.risk_indicator if e.control else "High Risk"
                    if indicator not in comms_risk_info[cid_str]:
                        comms_risk_info[cid_str].append(indicator)
                    
                    # Add matched keywords if any
                    if e.matched_keywords:
                        for kw in e.matched_keywords:
                            if kw not in comms_matched_keywords[cid_str]:
                                comms_matched_keywords[cid_str].append(kw)

                # 4. Map to ThreadMessage schema
                # We fetch content from ES if Postgres is null
                from modules.domains.b2b.bank_surveillance.services.rag import communication_rag_service
                
                alert.conversation_thread = []
                for c in thread_comms:
                    # Fallback to ES if content is null
                    content = c.content
                    if not content and c.message_id:
                        content = await communication_rag_service.get_content_by_id(str(c.message_id))
                    
                    cid_str = str(c.id)
                    alert.conversation_thread.append(ThreadMessage(
                        id=c.id,
                        sender=c.sender,
                        subject=c.subject,
                        content=content,
                        timestamp=c.timestamp,
                        is_trigger=cid_str in comms_risk_info,
                        risk_indicators=comms_risk_info.get(cid_str, []),
                        matched_keywords=comms_matched_keywords.get(cid_str, [])
                    ))
                    
        # Set assignee name
        if alert.assignee:
            alert.assignee_name = alert.assignee.name or alert.assignee.email
            
        return alert

    async def get_alert_stats(self, db: AsyncSession, tenant_id: UUID) -> AlertStats:
        """Get summary statistics for the Alerts Dashboard."""
        
        # 1. Total Alerts
        total_stmt = select(func.count(Alert.id)).where(Alert.tenant_id == tenant_id)
        total_res = await db.execute(total_stmt)
        total = total_res.scalar() or 0
        
        # 2. High/Critical Risk Count
        high_risk_stmt = select(func.count(Alert.id)).where(
            Alert.tenant_id == tenant_id,
            Alert.severity.in_([AlertSeverity.HIGH.value, AlertSeverity.CRITICAL.value])
        )
        high_res = await db.execute(high_risk_stmt)
        high_count = high_res.scalar() or 0
        
        # 3. Open Count
        open_stmt = select(func.count(Alert.id)).where(
            Alert.tenant_id == tenant_id,
            Alert.status == AlertStatus.OPEN.value
        )
        open_res = await db.execute(open_stmt)
        open_count = open_res.scalar() or 0
        
        # 4. Unassigned Count
        unassigned_stmt = select(func.count(Alert.id)).where(
            Alert.tenant_id == tenant_id,
            Alert.assigned_to.is_(None)
        )
        unassigned_res = await db.execute(unassigned_stmt)
        unassigned_count = unassigned_res.scalar() or 0
        
        return AlertStats(
            total_alerts=total,
            high_risk_count=high_count,
            open_count=open_count,
            unassigned_count=unassigned_count
        )

    async def list_alerts(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        filters: AlertFilter,
        limit: int = 50, 
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_desc: bool = True
    ) -> Tuple[List[Alert], int]:
        """List alerts with filtering"""
        query = select(Alert).where(Alert.tenant_id == tenant_id)
        
        # Join Communication and Region for listing
        query = query.outerjoin(Communication, Alert.communication_id == Communication.id)
        query = query.outerjoin(GeographicRegion, Communication.data_region_id == GeographicRegion.id)
        query = query.options(
            selectinload(Alert.communication).selectinload(Communication.region),
            selectinload(Alert.assignee)
        )
        
        # Apply filters
        if filters.status:
            query = query.where(Alert.status == filters.status.value)
        if filters.severity:
            query = query.where(Alert.severity == filters.severity.value)
        if filters.risk_type:
            query = query.where(Alert.risk_type == filters.risk_type.value)
        if filters.assigned_to:
            query = query.where(Alert.assigned_to == filters.assigned_to)
        if filters.communication_id:
            query = query.where(Alert.communication_id == filters.communication_id)
        if filters.region:
            query = query.where(GeographicRegion.name == filters.region)
            
        if filters.region:
            query = query.where(GeographicRegion.name == filters.region)
            
        # Get total count (before pagination)
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Pagination & Sorting
        if sort_by:
            # Handle sorting
            sort_column = getattr(Alert, sort_by, Alert.detected_at)
            
            # Special case for severity (Enum) - simplistic for now
            
            if sort_desc:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            # Default
            query = query.order_by(Alert.detected_at.desc())
        
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        for alert in alerts:
            # Set region name if available
            if alert.communication and alert.communication.region:
                alert.region = alert.communication.region.name
            else:
                alert.region = "Default"
                
            # Set assignee name
            if alert.assignee:
                alert.assignee_name = alert.assignee.name or alert.assignee.email
            else:
                alert.assignee_name = "Unassigned"

        return list(alerts), total

    async def update_alert(
        self, 
        db: AsyncSession, 
        alert_id: UUID, 
        tenant_id: UUID, 
        alert_in: AlertUpdate
    ) -> Optional[Alert]:
        """Update alert fields"""
        # First check existence and ownership
        alert = await self.get_alert(db, alert_id, tenant_id)
        if not alert:
            return None
            
        # Update fields
        update_data = alert_in.model_dump(exclude_unset=True)
        
        # Handle Enum to value conversion
        if 'status' in update_data and update_data['status']:
            update_data['status'] = update_data['status'].value
        if 'severity' in update_data and update_data['severity']:
            update_data['severity'] = update_data['severity'].value
        if 'metadata' in update_data:
            update_data['metadata_'] = update_data.pop('metadata')
            
        # Apply updates
        for field, value in update_data.items():
            setattr(alert, field, value)
            
        await db.flush()
        await db.refresh(alert)
        return alert

    async def escalate_alert(self, db: AsyncSession, alert_id: UUID, tenant_id: UUID) -> Optional[Alert]:
        """Shortcut to escalate and automatically create a case."""
        alert = await self.get_alert(db, alert_id, tenant_id)
        if not alert:
            return None
            
        # 1. Update Alert Status
        alert.status = AlertStatus.ESCALATED.value
        db.add(alert)
        
        # 2. Create a Corresponding Case (Delayed import to avoid circular dependencies)
        from modules.domains.b2b.bank_surveillance.services.case_service import case_service
        from modules.domains.b2b.bank_surveillance.schemas.case import CaseCreate, CaseEvidenceCreate
        
        case_in = CaseCreate(
            title=f"Investigation: {alert.risk_type.replace('_', ' ').capitalize()}",
            description=f"Automated case created from escalated alert: {alert.description}",
            priority=alert.severity, # Map critical/high/medium directly
            status="open",
            assigned_to_user_id=alert.assigned_to,
            source_uuid=alert.id, # Pass alert UUID to ensure numeric ID consistency
            initial_evidence=[
                CaseEvidenceCreate(
                    evidence_type="alert",
                    evidence_id=alert.id,
                    notes="Source Alert"
                )
            ]
        )
        
        # If alert is linked to a specific communication, add it as evidence
        if alert.communication_id:
            case_in.initial_evidence.append(
                CaseEvidenceCreate(
                    evidence_type="communication",
                    evidence_id=alert.communication_id,
                    notes="Flagged Communication"
                )
            )

        await case_service.create_case(db, case_in, tenant_id)
        
        await db.flush()
        await db.refresh(alert)
        return alert

    async def close_alert(self, db: AsyncSession, alert_id: UUID, tenant_id: UUID) -> Optional[Alert]:
        """Shortcut to close"""
        return await self.update_alert(
            db, alert_id, tenant_id, AlertUpdate(status=AlertStatus.CLOSED)
        )

alert_service = AlertService()
