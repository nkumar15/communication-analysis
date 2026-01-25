from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
from datetime import datetime

from modules.domains.b2b.bank_surveillance.models.case import Case, CaseNote, CaseEvidence
from modules.domains.b2b.bank_surveillance.schemas.case import CaseCreate, CaseUpdate, CaseNoteCreate, CaseEvidenceCreate, CaseStats
from sqlalchemy.orm import selectinload

class CaseService:
    async def create_case(self, db: AsyncSession, obj_in: CaseCreate, tenant_id: uuid.UUID) -> Case:
        """
        Create a new surveillance case with optional initial note and evidence.
        """
        db_obj = Case(
            tenant_id=tenant_id,
            title=obj_in.title,
            description=obj_in.description,
            priority=obj_in.priority,
            status=obj_in.status,
            assigned_to_user_id=obj_in.assigned_to_user_id,
            data_region_id=obj_in.data_region_id,
            sensitivity_level_id=obj_in.sensitivity_level_id,
            target_closure_date=obj_in.target_closure_date
        )
        db.add(db_obj)
        await db.flush() # Ensure we have the case ID for child relations

        if obj_in.initial_note:
            note = CaseNote(
                case_id=db_obj.id,
                content=obj_in.initial_note,
                author_id=obj_in.assigned_to_user_id
            )
            db.add(note)

        if obj_in.initial_evidence:
            for ev in obj_in.initial_evidence:
                evidence = CaseEvidence(
                    case_id=db_obj.id,
                    evidence_type=ev.evidence_type,
                    evidence_id=ev.evidence_id,
                    notes=ev.notes
                )
                db.add(evidence)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_case(self, db: AsyncSession, case_id: uuid.UUID) -> Optional[Case]:
        """Fetch a single case by ID with its relations enriched."""
        result = await db.execute(
            select(Case)
            .where(Case.id == case_id)
            .options(
                selectinload(Case.notes).selectinload(CaseNote.author),
                selectinload(Case.evidence)
            )
        )
        db_obj = result.scalars().first()
        if db_obj:
            # Populate author names for notes
            for note in db_obj.notes:
                if note.author:
                    note.author_name = note.author.full_name or note.author.email
                else:
                    note.author_name = "System"
        return db_obj

    async def get_case_stats(self, db: AsyncSession, tenant_id: uuid.UUID) -> CaseStats:
        """Get summary statistics for cases."""
        from sqlalchemy import func
        
        counts = {}
        for status in ["open", "in_review", "escalated"]:
            res = await db.execute(
                select(func.count(Case.id)).where(Case.tenant_id == tenant_id, Case.status == status)
            )
            counts[status] = res.scalar() or 0
            
        total_res = await db.execute(
            select(func.count(Case.id)).where(Case.tenant_id == tenant_id)
        )
        total = total_res.scalar() or 0
        
        return CaseStats(
            open_count=counts["open"],
            in_review_count=counts["in_review"],
            escalated_count=counts["escalated"],
            total_count=total
        )

    async def list_cases(self, db: AsyncSession, tenant_id: uuid.UUID, status: Optional[str] = None) -> List[Case]:
        """List all cases for a tenant, optionally filtered by status."""
        query = select(Case).where(Case.tenant_id == tenant_id)
        if status:
            query = query.where(Case.status == status)
        query = query.order_by(Case.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()

    async def update_case(self, db: AsyncSession, case_id: uuid.UUID, obj_in: CaseUpdate) -> Optional[Case]:
        """Update case metadata and handle status transitions (e.g., closing)."""
        db_obj = await self.get_case(db, case_id)
        if not db_obj:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle closure logic
        if update_data.get("status") == "closed":
            if not update_data.get("closed_at"):
                update_data["closed_at"] = datetime.utcnow()
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def add_note(self, db: AsyncSession, case_id: uuid.UUID, obj_in: CaseNoteCreate, author_id: uuid.UUID) -> CaseNote:
        """Add a new internal note to the case timeline."""
        note = CaseNote(
            case_id=case_id,
            content=obj_in.content,
            author_id=author_id
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    async def add_evidence(self, db: AsyncSession, case_id: uuid.UUID, obj_in: CaseEvidenceCreate) -> CaseEvidence:
        """Link a communication or alert to the case as evidence."""
        evidence = CaseEvidence(
            case_id=case_id,
            evidence_type=obj_in.evidence_type,
            evidence_id=obj_in.evidence_id,
            notes=obj_in.notes
        )
        db.add(evidence)
        await db.flush()
        await db.refresh(evidence)
        return evidence

case_service = CaseService()
