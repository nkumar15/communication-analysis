from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

class CommunicationResponse(BaseModel):
    id: uuid.UUID
    channel: str
    sender: str
    recipients: List[str]
    subject: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[Any] = None

    class Config:
        orm_mode = True


