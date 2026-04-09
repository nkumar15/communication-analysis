"""
Organizational Tier Model

Reference table for team hierarchy tiers (GLOBAL, REGIONAL, COUNTRY, BRANCH).
"""
from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text


class OrgTier(Base, TimestampMixin):
    """Org tier reference - defines valid organizational tiers for teams"""
    __tablename__ = "org_tiers"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='ux_org_tier_tenant_name'),
        {'schema': 'b2b'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete="CASCADE"), nullable=False)
    
    name = Column(String(20), nullable=False)  # GLOBAL, REGIONAL, COUNTRY, BRANCH
    display_name = Column(String(50), nullable=False)
    description = Column(Text)
    hierarchy_order = Column(Integer, nullable=False, default=0)  # Lower = broader tier
