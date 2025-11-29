from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID

class PlatformRole(Base, TimestampMixin):
    """
    Platform Role model - Roles specific to platform users.
    
    Examples: platform_admin, support_staff, billing_manager
    Completely separate from customer tenant roles.
    """
    __tablename__ = "platform_roles"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    
    is_system_role = Column(Boolean, default=False, nullable=False)  # Cannot delete if true


class PlatformUser(Base, TimestampMixin):
    """
    Platform User model - ALL platform users (admins, support, billing, etc.)
    
    These are users who work for/with the platform itself, not customer tenant users.
    Stored in a completely separate table from customer users.
    """
    __tablename__ = "platform_users"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    platform_role_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_roles.id'), nullable=False, index=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    firebase_uid = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
