from sqlalchemy import Column, String, UUID, DateTime, text, Enum as SQLEnum, JSON
from core.models.base import Base, TimestampMixin
import enum

class WorkspaceType(str, enum.Enum):
    """Workspace type enumeration"""
    personal = 'personal'
    team = 'team'

class Workspace(Base, TimestampMixin):
    """
    B2C Workspace model
    
    Represents either a personal workspace (1 user) or team workspace (multiple users).
    """
    __tablename__ = "workspaces"
    __table_args__ = {'schema': 'b2c'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(WorkspaceType, name='workspace_type', schema='b2c'), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    subscription_tier = Column(String(50), default='free')
    settings = Column(JSON, default={})
