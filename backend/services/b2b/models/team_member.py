from core.models.base import Base, TimestampMixin
from sqlalchemy import Column, String, ForeignKey, text, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

class TeamMember(Base, TimestampMixin):
    """Team membership with team-specific roles"""
    __tablename__ = "team_members"
    __table_args__ = (
        CheckConstraint("team_role IN ('team_manager', 'team_member', 'team_viewer')", name='valid_team_role'),
        {'schema': 'b2b'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"), index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey('b2b.teams.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Team-specific role
    team_role = Column(String(50), nullable=False, default='team_member', index=True)
    
    # Timestamps
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("UserModel")
