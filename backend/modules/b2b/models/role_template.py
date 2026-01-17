from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, Boolean, Text, text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB

class RoleTemplate(Base, TimestampMixin):
    """
    Template for creating roles in new tenants.
    Allows dynamic configuration of default roles without code changes.
    """
    __tablename__ = "role_templates"
    __table_args__ = {'schema': 'b2b'}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(50), unique=True, nullable=False)  # e.g. 'admin', 'field_manager'
    display_name = Column(String(100), nullable=False)      # e.g. 'Admin', 'Field Manager'
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)         # If true, cannot be deleted from tenant
    
    # List of permissions: [{'resource': 'users', 'actions': ['read', 'write']}]
    permissions = Column(JSONB, nullable=False, default=list)
    clearance_level = Column(Integer, default=1)
    
    # If true, this role is automatically seeded for every new tenant
    is_default = Column(Boolean, default=False, index=True)
