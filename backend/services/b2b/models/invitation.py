from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID

class InvitationModel(Base, TimestampMixin):
    """Customer Tenant Invitation ORM model"""
    __tablename__ = "invitations"
    __table_args__ = {'schema': 'b2b'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), default='field_agent', nullable=False)
    
    # Invitation token
    invitation_token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey('b2b.teams.id'), nullable=True, index=True)
    team_role = Column(String(50), nullable=True)  # NEW: Team role for auto-assignment
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    accepted_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=True)
    accepted_from_ip = Column(String(45), nullable=True)
