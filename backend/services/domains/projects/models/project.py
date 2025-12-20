"""Project ORM model"""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.models.base import Base, TimestampMixin, SoftDeleteMixin


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """Project model - containers for tasks, scoped to teams"""
    __tablename__ = "projects"
    __table_args__ = {'schema': 'domain'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey('b2b.teams.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Project details
    name = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default='active', nullable=False, index=True)
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id'), nullable=False, index=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
