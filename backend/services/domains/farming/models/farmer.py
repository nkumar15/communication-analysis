from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from services.b2b.models.tenant import TenantModel
from services.b2b.models.user import UserModel

class Farmer(Base, TimestampMixin):
    """Farmer management with row-level security"""
    __tablename__ = "farmers"
    __table_args__ = {'schema': 'farming'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Farmer details
    name = Column(String(200), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    
    # Row-level security (ownership tracking)
    created_by = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id"), nullable=False)
    
    # Relationships
    tenant = relationship(TenantModel)
    creator = relationship(UserModel, foreign_keys=[created_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_farmers_tenant_id', 'tenant_id'),
        Index('idx_farmers_created_by', 'created_by'),
        Index('idx_farmers_email', 'email'),
        {'schema': 'farming'}
    )
