from uuid import UUID
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, func
from sqlalchemy.orm import selectinload

from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus
from modules.domains.b2b.bank_surveillance.schemas.alert import AlertCreate, AlertUpdate, AlertFilter

class AlertService:
    async def create_alert(self, db: AsyncSession, alert_in: AlertCreate) -> Alert:
        """Create a new alert"""
        db_alert = Alert(
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
        db.add(db_alert)
        await db.flush()
        await db.refresh(db_alert)
        return db_alert

    async def get_alert(self, db: AsyncSession, alert_id: UUID, tenant_id: UUID) -> Optional[Alert]:
        """Get alert by ID and tenant"""
        stmt = select(Alert).where(
            Alert.id == alert_id,
            Alert.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_alerts(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        filters: AlertFilter,
        limit: int = 50, 
        offset: int = 0
    ) -> Tuple[List[Alert], int]:
        """List alerts with filtering"""
        query = select(Alert).where(Alert.tenant_id == tenant_id)
        
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
            
        # Get total count (before pagination)
        # Note: Optimization - simpler count query can be separate if performance needed
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Pagination & Sorting
        # Default sort: Severity (Critical first), then Detected At (Newest first)
        # Check if severity sort works with strings (Critical > High > Medium > Low)? 
        # Actually alphabetical is Critical < High. Enum order isn't preserved in DB string.
        # For MVP, just sort by detected_at desc.
        query = query.order_by(Alert.detected_at.desc())
        
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        alerts = result.scalars().all()
        
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
        """Shortcut to escalate"""
        return await self.update_alert(
            db, alert_id, tenant_id, AlertUpdate(status=AlertStatus.ESCALATED)
        )

    async def close_alert(self, db: AsyncSession, alert_id: UUID, tenant_id: UUID) -> Optional[Alert]:
        """Shortcut to close"""
        return await self.update_alert(
            db, alert_id, tenant_id, AlertUpdate(status=AlertStatus.CLOSED)
        )

alert_service = AlertService()
