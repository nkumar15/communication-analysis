from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, UUID, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

class GeographicRegion(Base, TimestampMixin):
    __tablename__ = "geographic_regions"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id'), nullable=False)
    code = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    parent_region_id = Column(UUID(as_uuid=True), ForeignKey('b2b.geographic_regions.id'))
    regulatory_jurisdiction = Column(String(50))
    data_residency_rules = Column(JSONB)
    
    parent = relationship("GeographicRegion", remote_side=[id], backref="children")
