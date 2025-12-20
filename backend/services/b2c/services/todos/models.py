from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from core.models.base import Base, TimestampMixin

class B2CTodo(Base, TimestampMixin):
    """B2C Todo Item - Implements the Workspace Container Pattern"""
    __tablename__ = "items"
    __table_args__ = {'schema': 'b2c_todos'}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    
    # The Container Link: Links this domain item to the workspace infrastructure
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('b2c.workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    is_completed = Column(Boolean, default=False, nullable=False)
    due_date = Column(DateTime(timezone=True))
    
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2c.users.id'), nullable=True)
