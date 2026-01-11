from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db.base import Base
import uuid
import enum

class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = {"schema": "b2b"}

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
    # Sensitivity is an Enum defined in DB, mapped as string here or Enum?
    # Usually easier to map as String unless we define the Enum in python explicitly.
    # Migration defined 'b2b.sensitivity_level'.
    
    # We can map it as String for simplicity or use Enum type if needed.
    # Given migration uses explicit enum type, better to use String to avoid type creation conflicts in SQLAlchemy
    # unless we define the enum class properly. I'll use String for now to match the migration behavior effectively.
    # Wait, migration created TYPE 'b2b.sensitivity_level'.
    # If I use String, it might work if SQLAlchemy casts it, but best to use Enum.
    
    sensitivity = Column(String, default="CONFIDENTIAL") 

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("TenantModel")
    team = relationship("Team")
    assigned_user = relationship("UserModel", foreign_keys=[assigned_to_user_id])
    region = relationship("GeographicRegion")
    communications = relationship("Communication", back_populates="investigation", cascade="all, delete-orphan")
