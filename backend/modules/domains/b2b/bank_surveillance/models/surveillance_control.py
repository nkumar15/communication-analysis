import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin

class SurveillanceControl(Base, TimestampMixin):
    __tablename__ = "surveillance_controls"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    risk_typology = Column(String(100), nullable=False)
    risk_indicator = Column(String(100), nullable=False)
    
    regulatory_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.regulatory_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    regulatory_reference_text = Column(String(255))
    
    detection_methods = Column(JSONB, default=list) # e.g. ["Keyword", "Semantic"]
    status = Column(String(50), default="Active")

    # Relationships
    regulatory_document = relationship("RegulatoryDocument")
