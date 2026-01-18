from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin
import uuid
import enum
from modules.b2b.models.sensitivity_level import SensitivityLevel


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("b2b.teams.id", ondelete="SET NULL"), nullable=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(20), default="medium")
    status = Column(String(50), default="open")
    
    # Plugin Metadata
    data_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id"), nullable=True)
    sensitivity_level_id = Column(UUID(as_uuid=True), ForeignKey("b2b.sensitivity_levels.id"), nullable=True)

    # created_at/updated_at by Mixin
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)


    # Relationships
    tenant = relationship("TenantModel")
    team = relationship("Team")
    assigned_user = relationship("UserModel", foreign_keys=[assigned_to_user_id])
    region = relationship("GeographicRegion")
    sensitivity_level = relationship("SensitivityLevel")
    communications = relationship("Communication", back_populates="investigation", cascade="all, delete-orphan")

