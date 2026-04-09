from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin
import uuid

class Case(Base, TimestampMixin):
    """
    Core model for Case Management lifecycle.
    """
    __tablename__ = "cases"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("b2b.teams.id", ondelete="SET NULL"), nullable=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(200), nullable=False)
    display_id = Column(String(20), unique=True, index=True) # CAS-1845192
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(50), default="open") # open, in_review, escalated, closed
    
    # Plugin Metadata (Region/Sensitivity isolation)
    data_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id"), nullable=True)
    sensitivity_level_id = Column(UUID(as_uuid=True), ForeignKey("b2b.sensitivity_levels.id"), nullable=True)

    # SLA & Outcomes
    target_closure_date = Column(TIMESTAMP(timezone=True), nullable=True)
    decision_rationale = Column(Text, nullable=True)
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("TenantModel")
    team = relationship("Team")
    assigned_user = relationship("UserModel", foreign_keys=[assigned_to_user_id])
    region = relationship("GeographicRegion")
    sensitivity_level = relationship("SensitivityLevel")
    
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("CaseEvidence", back_populates="case", cascade="all, delete-orphan")


class CaseNote(Base):
    """
    Internal discussion thread for a case.
    """
    __tablename__ = "case_notes"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.cases.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)

    case = relationship("Case", back_populates="notes")
    author = relationship("UserModel", foreign_keys=[author_id])


class CaseEvidence(Base):
    """
    Links between a case and evidence records (communications, alerts).
    """
    __tablename__ = "case_evidence"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.cases.id", ondelete="CASCADE"), nullable=False)
    evidence_type = Column(String(50), nullable=False) # 'communication', 'alert'
    evidence_id = Column(UUID(as_uuid=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)

    case = relationship("Case", back_populates="evidence")
