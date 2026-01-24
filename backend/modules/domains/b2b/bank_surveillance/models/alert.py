
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin

class AlertStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    CLOSED = "closed"
    FALSE_POSITIVE = "false_positive"

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskType(str, Enum):
    INSIDER_TRADING = "insider_trading"
    OFF_CHANNEL = "off_channel"
    SENTIMENT_NEGATIVE = "sentiment_negative"
    KEYWORD_MATCH = "keyword_match"

class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    communication_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.communications.id"), nullable=True, index=True)  # Legacy, nullable for new workflow
    
    subject = Column(String(255), nullable=True)  # Auto-generated: "{Sender} - {Indicator} - {Date}"
    risk_type = Column(String, nullable=True)  # Legacy field
    severity = Column(String, nullable=False)
    status = Column(String, default=AlertStatus.OPEN.value, nullable=False)
    
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id"), nullable=True)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict) # 'metadata' is reserved in SQLAlchemy Base
    
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    communication = relationship("Communication", backref="alerts")
    assignee = relationship("UserModel")
    incidents = relationship("Incident", back_populates="alert")
