from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

class PlatformPermission(Base, TimestampMixin):
    """
    Platform Permission model
    
    Granular permissions assigned to a PlatformRole.
    Example: role='support_staff' has permission(resource='tenants', action='read')
    """
    __tablename__ = "platform_permissions"
    __table_args__ = (
        UniqueConstraint('platform_role_id', 'resource', 'action', name='uq_role_resource_action'),
        {'schema': 'platform'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_role_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_roles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    resource = Column(String(50), nullable=False) # e.g. 'tenants', 'billing', 'users'
    action = Column(String(50), nullable=False)   # e.g. 'read', 'write', 'delete', 'impersonate'
