import uuid
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from core.db.base import Base, TimestampMixin

class RegulatoryDocument(Base, TimestampMixin):
    __tablename__ = "regulatory_documents"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    framework = Column(String(100))
    region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id"), nullable=True, index=True)
    year = Column(Integer)
    version = Column(String(20))
    storage_path = Column(String)
