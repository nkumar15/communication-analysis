from sqlalchemy import Column, String, Integer, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from core.db.base import Base, TimestampMixin
import uuid

class SensitivityLevel(Base, TimestampMixin):
    __tablename__ = "sensitivity_levels"
    __table_args__ = {"schema": "b2b"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    level = Column(Integer, nullable=False) # Comparison value
    description = Column(Text, nullable=True)

