"""B2C Workspace Invitation Model"""
from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, text
from core.db.base import Base

class WorkspaceInvitation(Base):
    """
    B2C Workspace Invitation model
    
    Represents an invitation to join a team workspace.
    Uses soft delete pattern for audit trail.
    Expires after 7 days if not accepted.
    """
    __tablename__ = "workspace_invitations"
    __table_args__ = {'schema': 'b2c'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('b2c.workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default='member')  # owner, admin, member, viewer
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('b2c.users.id', ondelete='CASCADE'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey('b2c.users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))
    
    # Relationships
    from sqlalchemy.orm import relationship
    workspace = relationship("Workspace", lazy="selectin")
    inviter = relationship("B2CUser", foreign_keys=[invited_by], lazy="selectin")
