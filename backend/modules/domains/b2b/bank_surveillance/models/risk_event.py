"""
RiskEvent Model - Tier 1: Individual Signal Evidence

Represents a single detection match between a message and a surveillance control.
"""
import uuid
from sqlalchemy import Column, String, Float, Text, ForeignKey, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin


class RiskEvent(Base, TimestampMixin):
    """Individual detection match between a Communication and a SurveillanceControl."""
    __tablename__ = "risk_events"
    __table_args__ = (
        UniqueConstraint('communication_id', 'control_id', name='uq_riskevent_comm_control'),
        {"schema": "bank_surveillance"}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    communication_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.communications.id", ondelete="CASCADE"), nullable=False, index=True)
    control_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.surveillance_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Denormalized for aggregation queries
    sender = Column(String(200), nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    
    # Detection evidence
    match_type = Column(String(50), nullable=False)  # "keyword", "regex", "ml"
    matched_keywords = Column(JSONB, default=list)
    matched_snippet = Column(Text, nullable=True)
    match_score = Column(Float, default=1.0)
    
    # Link to aggregated incident (set during aggregation phase)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relationships
    communication = relationship("Communication", backref="risk_events")
    control = relationship("SurveillanceControl", backref="risk_events")
    incident = relationship("Incident", back_populates="events")
