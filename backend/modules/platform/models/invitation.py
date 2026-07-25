from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, text
from sqlalchemy.dialects.postgresql import UUID
import enum

class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

class PlatformInvitation(Base, TimestampMixin):
    """
    Platform Invitation model
    
    Invitations for new platform users (admins, support, etc.)
    """
    __tablename__ = "platform_invitations"
    __table_args__ = {'schema': 'platform'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    platform_tenant_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_tenant.id', ondelete='CASCADE'), nullable=False)
    
    email = Column(String(255), nullable=False, index=True)
    platform_role_id = Column(UUID(as_uuid=True), ForeignKey('platform.platform_roles.id'), nullable=False)
    
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    invited_by = Column(UUID(as_uuid=True), ForeignKey('platform.platform_users.id'), nullable=False)
    status = Column(
        Enum(InvitationStatus, name='invitation_status', schema='platform', values_callable=lambda x: [e.value for e in x]),
        default=InvitationStatus.PENDING,
        nullable=False
    )
