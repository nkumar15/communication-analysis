from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Index, Integer, text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .tenant import TenantModel
from .user import UserModel

class Role(Base, TimestampMixin):
    """User roles with configurable permissions"""
    __tablename__ = "roles"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)  # Internal: 'admin', 'field_manager'
    display_name = Column(String(100), nullable=False)  # UI: 'Admin', 'Field Manager'
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Relationships
    tenant = relationship(TenantModel)
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship(UserModel, foreign_keys=[UserModel.role_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_roles_tenant_id', 'tenant_id'),
        Index('idx_roles_name', 'name'),
        {'schema': 'b2b'}
    )


class Resource(Base, TimestampMixin):
    """Application resources that can be controlled by permissions"""
    __tablename__ = "resources"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(50), unique=True, nullable=False)  # 'dashboard', 'users', 'shops'
    display_name = Column(String(100), nullable=False)  # 'Dashboard', 'User Management'
    category = Column(String(50))  # Group in UI: 'Administration', 'Core'
    description = Column(Text)
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="resource")


class Action(Base, TimestampMixin):
    """Generic actions that can be performed on resources"""
    __tablename__ = "actions"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # 'read', 'write', 'delete'
    display_name = Column(String(100), nullable=False)  # 'View', 'Create/Edit', 'Delete'
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="action")


class RolePermission(Base):
    """Maps roles to resource+action combinations"""
    __tablename__ = "role_permissions"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id = Column(UUID(as_uuid=True), ForeignKey("b2b.roles.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("b2b.resources.id", ondelete="CASCADE"), nullable=False)
    action_id = Column(UUID(as_uuid=True), ForeignKey("b2b.actions.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    resource = relationship("Resource", back_populates="permissions")
    action = relationship("Action", back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_role_permissions_role_id', 'role_id'),
        Index('idx_role_permissions_resource_id', 'resource_id'),
        Index('idx_role_permissions_action_id', 'action_id'),
        {'schema': 'b2b'}
    )
