"""Task ORM model"""
from sqlalchemy import Column, String, Text, ForeignKey, Date, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.db.base import Base, TimestampMixin, SoftDeleteMixin


class Task(Base, TimestampMixin, SoftDeleteMixin):
    """Task model - work items within projects"""
    __tablename__ = "tasks"
    __table_args__ = {'schema': 'domain'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('domain.projects.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Task details
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default='todo', nullable=False, index=True)
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), index=True)
    
    # Dates
    due_date = Column(Date)
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=False, index=True)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
