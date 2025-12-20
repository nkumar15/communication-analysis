"""Comment ORM model"""
from sqlalchemy import Column, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.base import Base, TimestampMixin, SoftDeleteMixin


class Comment(Base, TimestampMixin, SoftDeleteMixin):
    """Comment model - threaded comments on tasks"""
    __tablename__ = "comments"
    __table_args__ = {'schema': 'domain'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey('domain.tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Comment content
    content = Column(Text, nullable=False)
    
    # Threading support
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey('domain.comments.id', ondelete='CASCADE'), index=True)
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=False, index=True)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    replies = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
