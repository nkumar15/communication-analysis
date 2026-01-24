"""
Incident Model - Tier 2: Aggregated Signals

Represents a grouping of RiskEvents by sender, control, and date.
"""
import uuid
from enum import Enum
from sqlalchemy import Column, String, Integer, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin


class IncidentStatus(str, Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    ESCALATED = "escalated"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident(Base, TimestampMixin):
    """Aggregation of RiskEvents per sender/day/control."""
    __tablename__ = "incidents"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    control_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.surveillance_controls.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sender = Column(String(200), nullable=False, index=True)
    incident_date = Column(Date, nullable=False, index=True)
    event_count = Column(Integer, default=1)
    
    severity = Column(String(20), default=IncidentSeverity.LOW.value)
    status = Column(String(20), default=IncidentStatus.OPEN.value)
    
    # Link to alert (set during alert generation)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Plugin Metadata (propagated from grouped events)
    data_region_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)  # Unique regions from grouped events
    sensitivity_level_id = Column(UUID(as_uuid=True), ForeignKey("b2b.sensitivity_levels.id", ondelete="SET NULL"), nullable=True)  # MAX classification
    
    # Relationships
    control = relationship("SurveillanceControl", backref="incidents")
    alert = relationship("Alert", back_populates="incidents")
    events = relationship("RiskEvent", back_populates="incident")
    sensitivity_level = relationship("SensitivityLevel")
    
    @staticmethod
    def calculate_severity(event_count: int) -> str:
        """Calculate severity based on event count."""
        if event_count >= 16:
            return IncidentSeverity.CRITICAL.value
        elif event_count >= 8:
            return IncidentSeverity.HIGH.value
        elif event_count >= 4:
            return IncidentSeverity.MEDIUM.value
        else:
            return IncidentSeverity.LOW.value
