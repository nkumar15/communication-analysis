from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from modules.domains.b2b.bank_surveillance.models.regulatory_document import RegulatoryDocument
from modules.domains.b2b.bank_surveillance.schemas.regulatory import RegulatoryDocumentCreate, RegulatoryDocumentUpdate

class RegulatoryService:
    async def create_document(self, db: AsyncSession, doc_in: RegulatoryDocumentCreate) -> RegulatoryDocument:
        """Create a new regulatory document"""
        db_doc = RegulatoryDocument(
            tenant_id=doc_in.tenant_id,
            title=doc_in.title,
            framework=doc_in.framework,
            region_id=doc_in.region_id,
            year=doc_in.year,
            version=doc_in.version,
            storage_path=doc_in.storage_path
        )
        db.add(db_doc)
        await db.flush()
        await db.refresh(db_doc)
        return db_doc

    async def get_document(self, db: AsyncSession, doc_id: UUID, tenant_id: UUID, access_scopes: Optional[List[UUID]] = None) -> Optional[RegulatoryDocument]:
        """Get document by ID and tenant, optionally verifying regional access."""
        stmt = select(RegulatoryDocument).where(
            RegulatoryDocument.id == doc_id,
            RegulatoryDocument.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record and access_scopes:
            if record.region_id and record.region_id not in access_scopes:
                return None
                
        return record

    async def list_documents(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        limit: int = 50, 
        offset: int = 0,
        access_scopes: Optional[List[UUID]] = None
    ) -> List[RegulatoryDocument]:
        """List regulatory documents for a tenant"""
        stmt = select(RegulatoryDocument).where(
            RegulatoryDocument.tenant_id == tenant_id
        )
        
        if access_scopes:
            from sqlalchemy import or_
            stmt = stmt.where(or_(
                RegulatoryDocument.region_id.is_(None),
                RegulatoryDocument.region_id.in_(access_scopes)
            ))
            
        stmt = stmt.order_by(RegulatoryDocument.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_document(
        self,
        db: AsyncSession,
        doc_id: UUID,
        tenant_id: UUID,
        doc_in: RegulatoryDocumentUpdate,
        access_scopes: Optional[List[UUID]] = None
    ) -> Optional[RegulatoryDocument]:
        """Update regulatory document"""
        db_doc = await self.get_document(db, doc_id, tenant_id, access_scopes)
        if not db_doc:
            return None
            
        update_data = doc_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_doc, field, value)
            
        await db.flush()
        await db.refresh(db_doc)
        return db_doc

    async def delete_document(self, db: AsyncSession, doc_id: UUID, tenant_id: UUID, access_scopes: Optional[List[UUID]] = None) -> bool:
        """Delete regulatory document"""
        db_doc = await self.get_document(db, doc_id, tenant_id, access_scopes)
        if not db_doc:
            return False
        
        await db.delete(db_doc)
        await db.flush()
        return True

regulatory_service = RegulatoryService()
