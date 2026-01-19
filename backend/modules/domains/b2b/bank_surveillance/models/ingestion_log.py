import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from core.db.base import Base

class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    __table_args__ = {"schema": "bank_surveillance"}

    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(String(8), nullable=False, index=True)  # YYYYMMDD
    status = Column(String, default="running", index=True) # running, completed, failed
    file_path = Column(String, nullable=False)
    
    processed_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
