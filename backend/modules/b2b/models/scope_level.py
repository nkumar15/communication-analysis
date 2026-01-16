"""
Organizational Tier Model

Reference table for team hierarchy tiers (GLOBAL, REGIONAL, COUNTRY, BRANCH).
"""
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

from core.db.base import Base, TimestampMixin


class OrgTier(Base, TimestampMixin):
    """Org tier reference - defines valid organizational tiers for teams"""
    __tablename__ = "org_tiers"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    
    name = Column(String(20), nullable=False, unique=True)  # GLOBAL, REGIONAL, COUNTRY, BRANCH
    display_name = Column(String(50), nullable=False)
    description = Column(Text)
    hierarchy_order = Column(Integer, nullable=False, default=0)  # Lower = broader tier
