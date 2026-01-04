from sqlalchemy import Column, String, DateTime, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func, text
import uuid

from core.db.base import Base, TimestampMixin

class EnronEmail(Base, TimestampMixin):
    __tablename__ = "enron_emails"
    __table_args__ = {"schema": "b2b_enron"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String, unique=True, nullable=False)
    sender = Column(String, nullable=False)
    recipients = Column(ARRAY(String), nullable=False)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
