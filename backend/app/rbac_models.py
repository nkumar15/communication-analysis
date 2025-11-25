"""
RBAC (Role-Based Access Control) Database Models

Models for roles, resources, actions, and permissions.
"""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db_models import Base, TenantModel as Tenant, UserModel as User
import uuid


class Role(Base):
    """User roles with configurable permissions"""
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)  # Internal: 'admin', 'field_manager'
    display_name = Column(String(100), nullable=False)  # UI: 'Admin', 'Field Manager'
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship(Tenant)
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship(User, foreign_keys=[User.role_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_roles_tenant_id', 'tenant_id'),
        Index('idx_roles_name', 'name'),
        {'schema': None}
    )


class Resource(Base):
    """Application resources that can be controlled by permissions"""
    __tablename__ = "resources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(50), unique=True, nullable=False)  # 'dashboard', 'users', 'farmers'
    display_name = Column(String(100), nullable=False)  # 'Dashboard', 'User Management'
    category = Column(String(50))  # Group in UI: 'Administration', 'Core'
    description = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="resource")


class Action(Base):
    """Generic actions that can be performed on resources"""
    __tablename__ = "actions"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # 'read', 'write', 'delete'
    display_name = Column(String(100), nullable=False)  # 'View', 'Create/Edit', 'Delete'
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="action")


class RolePermission(Base):
    """Maps roles to resource+action combinations"""
    __tablename__ = "role_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    action_id = Column(UUID(as_uuid=True), ForeignKey("actions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    resource = relationship("Resource", back_populates="permissions")
    action = relationship("Action", back_populates="permissions")
    
    # Indexes
    __table_args__ = (
        Index('idx_role_permissions_role_id', 'role_id'),
        Index('idx_role_permissions_resource_id', 'resource_id'),
        Index('idx_role_permissions_action_id', 'action_id'),
        {'schema': None}
    )


class Farmer(Base):
    """Farmer management with row-level security"""
    __tablename__ = "farmers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Farmer details
    name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    
    # Row-level security (ownership tracking)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship(Tenant)
    creator = relationship(User, foreign_keys=[created_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_farmers_tenant_id', 'tenant_id'),
        Index('idx_farmers_created_by', 'created_by'),
        Index('idx_farmers_email', 'email'),
        {'schema': None}
    )
