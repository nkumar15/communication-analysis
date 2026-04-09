from core.db.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, ForeignKey, text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship


class Team(Base, TimestampMixin, SoftDeleteMixin):
    """Team model for organizing users within a tenant"""
    __tablename__ = "teams"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Team information
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Management
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=True, index=True)
    
    # Organizational Tier: GLOBAL, REGIONAL, COUNTRY, BRANCH
    org_tier = Column(String(20), nullable=True)
    org_tier_id = Column(UUID(as_uuid=True), ForeignKey('b2b.org_tiers.id'), nullable=True)
    
    # Hierarchy
    parent_team_id = Column(UUID(as_uuid=True), ForeignKey('b2b.teams.id'))
    team_type = Column(String(50))
    hierarchy_level = Column(Integer, default=0)
    
    # Geographic plugin: link to a GeographicRegion for scope derivation
    region_id = Column(UUID(as_uuid=True), ForeignKey('b2b.geographic_regions.id', ondelete='SET NULL'), nullable=True, index=True)

    # config_data
    config_data = Column(JSONB, default={}, nullable=False, server_default='{}')
    
    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
