from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from core.db.base import Base

class RagDocument(Base):
    __tablename__ = "rag_documents"
    __table_args__ = {"schema": "b2b_nse"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("b2b.tenants.id", ondelete="CASCADE"), nullable=False)
    
    filename = Column(String(500), nullable=False)
    file_url = Column(String, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Metadata
    company_name = Column(String(200), nullable=True)
    report_type = Column(String(50), nullable=True)
    financial_period = Column(String(50), nullable=True)
    
    # Processing
    status = Column(String(20), server_default="pending", nullable=False)
    chunk_count = Column(Integer, server_default="0")
    es_indexed_count = Column(Integer, server_default="0")
    error_message = Column(String, nullable=True)
    
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("b2b.users.id"), nullable=True)
    
    # Async/Upsert fields
    job_id = Column(String(100), nullable=True)
    content_hash = Column(String(64), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
