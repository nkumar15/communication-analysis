"""
SQLAlchemy ORM models for tenants, users, and invitations
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


# ============================================================================
# CUSTOMER TENANT SYSTEM
# ============================================================================

class TenantModel(Base):
    """Customer Tenant ORM model"""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    firebase_tenant_id = Column(String(255), unique=True, nullable=False)
    oidc_provider_id = Column(String(255), nullable=True)
    
    # Activation fields
    activation_token = Column(String(64), unique=True, nullable=True, index=True)
    activation_status = Column(String(20), default='pending', nullable=False, index=True)
    activation_expires_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    activated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    activation_started_at = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserModel(Base):
    """Customer Tenant User ORM model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    firebase_uid = Column(String(255), nullable=False, index=True)
    
    # RBAC fields
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=True, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Self-referential relationship for invitation hierarchy
    invited_users = relationship("UserModel", backref="inviter", remote_side=[id], foreign_keys=[invited_by])


class InvitationModel(Base):
    """Customer Tenant Invitation ORM model"""
    __tablename__ = "invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), default='field_agent', nullable=False)
    
    # Invitation token
    invitation_token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    accepted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    accepted_from_ip = Column(String(45), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ============================================================================
# PLATFORM SYSTEM (Completely Separate)
# ============================================================================

class PlatformTenant(Base):
    """
    Platform Tenant model - Represents THE platform itself.
    
    This is a singleton table (only one row) representing the SaaS platform
    as an entity. Completely separate from customer tenants.
    """
    __tablename__ = "platform_tenant"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), nullable=False, default='SaaS Platform')
    firebase_tenant_id = Column(String(255), unique=True, nullable=False)
    oidc_provider_id = Column(String(255), nullable=True)
    
    # Configuration
    email_domain = Column(String(255), nullable=True)
    support_email = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlatformRole(Base):
    """
    Platform Role model - Roles specific to platform users.
    
    Examples: platform_admin, support_staff, billing_manager
    Completely separate from customer tenant roles.
    """
    __tablename__ = "platform_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(String, nullable=True)
    
    is_system_role = Column(Boolean, default=False, nullable=False)  # Cannot delete if true
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlatformUser(Base):
    """
    Platform User model - ALL platform users (admins, support, billing, etc.)
    
    These are users who work for/with the platform itself, not customer tenant users.
    Stored in a completely separate table from customer users.
    """
    __tablename__ = "platform_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    platform_role_id = Column(UUID(as_uuid=True), ForeignKey('platform_roles.id'), nullable=False, index=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    firebase_uid = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlatformAuditLog(Base):
    """
    Audit log for platform user actions.
    
    Tracks all actions performed by platform users for security,
    compliance, and debugging.
    """
    __tablename__ = "platform_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform_tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('platform_users.id', ondelete='SET NULL'), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Denormalized
    
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
