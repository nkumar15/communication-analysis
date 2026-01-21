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

    async def get_document(self, db: AsyncSession, doc_id: UUID, tenant_id: UUID) -> Optional[RegulatoryDocument]:
        """Get document by ID and tenant"""
        stmt = select(RegulatoryDocument).where(
            RegulatoryDocument.id == doc_id,
            RegulatoryDocument.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[RegulatoryDocument]:
        """List regulatory documents for a tenant"""
        stmt = select(RegulatoryDocument).where(
            RegulatoryDocument.tenant_id == tenant_id
        ).order_by(RegulatoryDocument.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_document(
        self, 
        db: AsyncSession, 
        doc_id: UUID, 
        tenant_id: UUID, 
        doc_in: RegulatoryDocumentUpdate
    ) -> Optional[RegulatoryDocument]:
        """Update regulatory document"""
        db_doc = await self.get_document(db, doc_id, tenant_id)
        if not db_doc:
            return None
            
        update_data = doc_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_doc, field, value)
            
        await db.flush()
        await db.refresh(db_doc)
        return db_doc

    async def delete_document(self, db: AsyncSession, doc_id: UUID, tenant_id: UUID) -> bool:
        """Delete regulatory document"""
        db_doc = await self.get_document(db, doc_id, tenant_id)
        if not db_doc:
            return False
        
        await db.delete(db_doc)
        await db.flush()
        return True

regulatory_service = RegulatoryService()
