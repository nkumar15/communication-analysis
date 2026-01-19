from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
import uuid

class EnronEmailBase(BaseModel):
    message_id: str
    sender: str
    recipients: List[str]
    subject: Optional[str] = None
    body: Optional[str] = None
    date: datetime

class EnronEmailCreate(EnronEmailBase):
    pass

class EnronEmailResponse(EnronEmailBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
