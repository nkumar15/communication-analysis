"""
Bulk Invite Job Model

Tracks bulk user invitation operations and stores detailed results.
"""

from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from core.db.base import Base


class BulkInviteJob(Base):
    """
    Stores bulk invitation job results.
    
    The results field contains JSONB with structure:
    {
        "rows": [
            {
                "row": 1,
                "email": "user@domain.com",
                "name": "User Name",
                "role": "admin",
                "team_name": "Engineering",
                "status": "success",
                "invitation_id": "uuid"
            },
            {
                "row": 2,
                "email": "invalid@wrong.com",
                "status": "error",
                "error": "Email domain mismatch"
            }
        ]
    }
    """
    
    __tablename__ = "bulk_invite_jobs"
    __table_args__ = (
        CheckConstraint('total_rows > 0', name='bulk_invite_jobs_total_rows_positive'),
        CheckConstraint('successful_count >= 0', name='bulk_invite_jobs_successful_count_non_negative'),
        CheckConstraint('failed_count >= 0', name='bulk_invite_jobs_failed_count_non_negative'),
        CheckConstraint(
            'successful_count + failed_count = total_rows',
            name='bulk_invite_jobs_counts_valid'
        ),
        {'schema': 'b2b'}
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('b2b.tenants.id', ondelete='CASCADE'), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('b2b.users.id', ondelete='SET NULL'), nullable=False)
    
    total_rows = Column(Integer, nullable=False)
    successful_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    
    results = Column(JSONB, nullable=False, default={'rows': []})
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships (use lazy loading, no back_populates to avoid TenantModel changes)
    tenant = relationship("TenantModel")
    creator = relationship("UserModel", foreign_keys=[created_by])
