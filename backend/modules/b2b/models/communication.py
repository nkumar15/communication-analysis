from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.db.base import Base
import uuid

class Communication(Base):
    __tablename__ = "communications"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey("b2b.investigations.id", ondelete="SET NULL"), nullable=True)
    
    channel = Column(String(50), nullable=False)
    sender = Column(String(200), nullable=False)
    recipient = Column(String(200), nullable=False)
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    flagged_keywords = Column(JSONB, default=list)
    
    # Plugin Metadata
    data_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id"), nullable=True)
    sensitivity = Column(String, default="INTERNAL")

    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tenant = relationship("TenantModel")
    investigation = relationship("Investigation", back_populates="communications")
    region = relationship("GeographicRegion")
