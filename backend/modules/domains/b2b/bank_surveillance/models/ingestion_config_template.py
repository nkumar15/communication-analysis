"""
IngestionConfigTemplate Model - Global template for ingestion configuration.

These templates are seeded from YAML and shared across all tenants.
Per-tenant configs are cloned from these templates during tenant onboarding.
"""
import uuid
from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from core.db.base import Base, TimestampMixin


class IngestionConfigTemplate(Base, TimestampMixin):
    """Global ingestion config template (shared across tenants)."""
    __tablename__ = "ingestion_config_templates"
    __table_args__ = {"schema": "bank_surveillance"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    
    # Region Detection Strategy
    region_strategy = Column(String(50), default="default")  # default | sender_lookup | content_rules
    sender_domain_map = Column(JSONB, default=dict)  # {"@bank-apac.com": "uuid"}
    
    # Classification Detection Strategy
    classification_strategy = Column(String(50), default="default")  # default | content_rules | channel_map
    channel_map = Column(JSONB, default=dict)  # {"bloomberg": "uuid-confidential"}
    content_rules = Column(JSONB, default=list)  # [{"pattern": "MNPI", "level_id": "uuid"}]
