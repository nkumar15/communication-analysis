from sqlalchemy import Column, String, UUID, DateTime, ForeignKey, text
from core.models.base import Base

class WorkspaceMember(Base):
    """
    B2C Workspace Member model
    
    Represents team workspace membership. Personal workspaces don't use this table.
    """
    __tablename__ = "workspace_members"
    __table_args__ = {'schema': 'b2c'}
    
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('b2c.workspaces.id', ondelete='CASCADE'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    role = Column(String(50), nullable=False, default='member')  # owner, admin, member
    joined_at = Column(DateTime, server_default=text("NOW()"))
    
    from sqlalchemy.orm import relationship
    workspace = relationship("Workspace", lazy="selectin")
