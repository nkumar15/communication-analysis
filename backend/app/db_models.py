"""
SQLAlchemy ORM models for tenants, users, and invitations
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class TenantModel(Base):
    """Tenant ORM model"""
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
    activation_started_at = Column(DateTime(timezone=True), nullable=True)  # Prevent replay attacks
    
    is_system_tenant = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UserModel(Base):
    """User ORM model - only for authenticated users with Firebase UID"""
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
    
    # Note: Unique constraints defined at table level in migrations
    # Note: RBAC relationships (role_obj, created_farmers) removed to avoid circular imports


class InvitationModel(Base):
    """Invitation ORM model - for pending user invitations"""
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
    
    # Audit fields for security
    accepted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Who accepted
    accepted_from_ip = Column(String(45), nullable=True)  # IP address of acceptance
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

