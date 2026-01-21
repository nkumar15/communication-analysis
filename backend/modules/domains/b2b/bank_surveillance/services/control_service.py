from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from modules.domains.b2b.bank_surveillance.models.surveillance_control import SurveillanceControl
from modules.domains.b2b.bank_surveillance.schemas.control import SurveillanceControlCreate, SurveillanceControlUpdate

class ControlService:
    async def create_control(self, db: AsyncSession, control_in: SurveillanceControlCreate) -> SurveillanceControl:
        """Create a new surveillance control"""
        db_control = SurveillanceControl(
            tenant_id=control_in.tenant_id,
            risk_typology=control_in.risk_typology,
            risk_indicator=control_in.risk_indicator,
            regulatory_id=control_in.regulatory_id,
            regulatory_reference_text=control_in.regulatory_reference_text,
            detection_methods=control_in.detection_methods,
            status=control_in.status
        )
        db.add(db_control)
        await db.flush()
        # Return fully loaded object
        return await self.get_control(db, db_control.id, db_control.tenant_id)

    async def get_control(self, db: AsyncSession, control_id: UUID, tenant_id: UUID) -> Optional[SurveillanceControl]:
        """Get surveillance control by ID and tenant"""
        stmt = select(SurveillanceControl).options(
            selectinload(SurveillanceControl.regulatory_document)
        ).where(
            SurveillanceControl.id == control_id,
            SurveillanceControl.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_controls(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        risk_typology: Optional[str] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[SurveillanceControl]:
        """List surveillance controls with optional filtering"""
        stmt = select(SurveillanceControl).options(
            selectinload(SurveillanceControl.regulatory_document)
        ).where(
            SurveillanceControl.tenant_id == tenant_id
        )
        
        if risk_typology:
            stmt = stmt.where(SurveillanceControl.risk_typology == risk_typology)
            
        stmt = stmt.order_by(SurveillanceControl.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_control(
        self, 
        db: AsyncSession, 
        control_id: UUID, 
        tenant_id: UUID, 
        control_in: SurveillanceControlUpdate
    ) -> Optional[SurveillanceControl]:
        """Update surveillance control"""
        db_control = await self.get_control(db, control_id, tenant_id)
        if not db_control:
            return None
            
        update_data = control_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_control, field, value)
            
        await db.flush()
        await db.refresh(db_control)
        return db_control

    async def delete_control(self, db: AsyncSession, control_id: UUID, tenant_id: UUID) -> bool:
        """Delete surveillance control"""
        db_control = await self.get_control(db, control_id, tenant_id)
        if not db_control:
            return False
            
        await db.delete(db_control)
        await db.flush()
        return True

control_service = ControlService()
