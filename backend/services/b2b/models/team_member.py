from core.db.base import Base, TimestampMixin
from sqlalchemy import Column, String, ForeignKey, text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class TeamMember(Base, TimestampMixin):
    """Team membership with team-specific roles"""
    __tablename__ = "team_members"
    __table_args__ = {'schema': 'b2b'}  # CHECK constraint removed in migration
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey('b2b.teams.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Team-specific role (legacy column - kept for backward compatibility)
    team_role = Column(String(50), nullable=False, default='team_contributor', index=True)
    
    # New team role FK (preferred)
    team_role_id = Column(UUID(as_uuid=True), ForeignKey('b2b.team_role_definitions.id'), nullable=True, index=True)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("UserModel")
    role_definition = relationship("TeamRoleDefinition")

