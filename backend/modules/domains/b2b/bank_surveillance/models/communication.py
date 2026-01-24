from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin
import uuid
from modules.b2b.models.sensitivity_level import SensitivityLevel


class Communication(Base, TimestampMixin):
    __tablename__ = "communications"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    
    channel = Column(String(50), nullable=False)
    sub_channel = Column(String(50), nullable=True)
    message_id = Column(String, unique=True, nullable=True) # Unique IF provided (e.g. Email ID)
    sender = Column(String(200), nullable=False, index=True)
    recipients = Column(ARRAY(String), nullable=False)  # Postgres Array
    subject = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    
    # Thread reconstruction
    thread_id = Column(String, nullable=True, index=True)
    
    # ES reference (content stored in ES for full-text search)
    es_document_id = Column(String, nullable=True, unique=True, index=True)
    
    # Processing state
    analyzed = Column(Boolean, default=False, index=True)
    
    # Plugin Metadata
    data_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id"), nullable=True)
    sensitivity_level_id = Column(UUID(as_uuid=True), ForeignKey("b2b.sensitivity_levels.id"), nullable=True)

    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    # created_at/updated_at by Mixin


    # Relationships
    tenant = relationship("TenantModel")
    region = relationship("GeographicRegion")
    sensitivity_level = relationship("SensitivityLevel")

