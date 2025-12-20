from core.models.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class PlatformRole(Base, TimestampMixin):
    """
    Platform Role model - System-level roles for platform users.
    
    Examples: platform_admin, support_staff, billing_manager
    These are system-level and independent of any platform tenant.
    """
    __tablename__ = "platform_roles"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    
    is_system_role = Column(Boolean, default=False, nullable=False)  # Cannot delete if true
    
    # Relationships
    permissions = relationship("PlatformPermission", backref="role", cascade="all, delete-orphan", lazy="selectin")


class PlatformUser(Base, TimestampMixin, SoftDeleteMixin):
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
