"""
Team Role Definition Model

Represents configurable team-level roles for domain resource access.
System roles (tenant_id=NULL) are global templates visible to all tenants.
"""
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

from core.db.base import Base, TimestampMixin


class TeamRoleDefinition(Base, TimestampMixin):
    """Team role definition - configurable team-level roles"""
    __tablename__ = "team_role_definitions"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=True, index=True)
    
    name = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Capability flags - REPLACED BY granular permissions
    # can_manage_members = Column(Boolean, default=False, nullable=False)
    # can_manage_settings = Column(Boolean, default=False, nullable=False)
    # can_write_resources = Column(Boolean, default=True, nullable=False)
    # can_delete_resources = Column(Boolean, default=False, nullable=False)
    
    # Granular Access Control
    from sqlalchemy.dialects.postgresql import JSONB
    permissions = Column(JSONB, default=list, nullable=False, server_default=text("'[]'::jsonb"))

    # Data Classification: minimum clearance level granted by this role.
    # 0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=RESTRICTED, 4=TOP_SECRET
    # Matches DataClassificationPlugin.SENSITIVITY_LEVELS scale.
    clearance_level = Column(Integer, default=1, nullable=False, server_default=text("1"))

    is_system = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Org Tier Enforcement: Array of allowed org tiers e.g. ['GLOBAL', 'REGIONAL']
    from sqlalchemy.dialects.postgresql import ARRAY
    allowed_org_tiers = Column(ARRAY(String), default=list, nullable=False, server_default=text("'{}'::varchar[]"))
