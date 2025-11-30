from core.models.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class UserModel(Base, TimestampMixin, SoftDeleteMixin):
    """Customer Tenant User ORM model"""
    __tablename__ = "users"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    firebase_uid = Column(String(255), nullable=False, index=True)
    
    # RBAC fields
    role_id = Column(UUID(as_uuid=True), ForeignKey('b2b.roles.id'), nullable=True, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=True, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Self-referential relationship for invitation hierarchy
    invited_users = relationship("UserModel", backref="inviter", remote_side=[id], foreign_keys=[invited_by])
