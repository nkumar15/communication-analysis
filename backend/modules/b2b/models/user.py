from core.db.base import Base, TimestampMixin, SoftDeleteMixin
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY

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
    geographic_scopes = Column(ARRAY(UUID(as_uuid=True)), default=list)
    
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
