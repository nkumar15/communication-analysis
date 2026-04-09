"""
IngestionConfig Model - Per-tenant ingestion configuration.

Cloned from IngestionConfigTemplate during tenant onboarding.
Tenants can customize their config after cloning.
"""
import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin


class IngestionConfig(Base, TimestampMixin):
    """Per-tenant ingestion configuration (cloned from template)."""
    __tablename__ = "ingestion_configs"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("bank_surveillance.ingestion_config_templates.id", ondelete="SET NULL"), nullable=True)
    
    # Region Detection (copied from template, customizable)
    region_strategy = Column(String(50), default="default")
    default_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id", ondelete="SET NULL"), nullable=True)
    fallback_region_id = Column(UUID(as_uuid=True), ForeignKey("b2b.geographic_regions.id", ondelete="SET NULL"), nullable=True)
    sender_domain_map = Column(JSONB, default=dict)
    
    # Classification Detection
    classification_strategy = Column(String(50), default="default")
    default_level_id = Column(UUID(as_uuid=True), ForeignKey("b2b.sensitivity_levels.id", ondelete="SET NULL"), nullable=True)
    channel_map = Column(JSONB, default=dict)
    content_rules = Column(JSONB, default=list)
    
    # Relationships
    template = relationship("IngestionConfigTemplate")
    default_region = relationship("GeographicRegion", foreign_keys=[default_region_id])
    fallback_region = relationship("GeographicRegion", foreign_keys=[fallback_region_id])
    default_sensitivity_level = relationship("SensitivityLevel", foreign_keys=[default_level_id])
