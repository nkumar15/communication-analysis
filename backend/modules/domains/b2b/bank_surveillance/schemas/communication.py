from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
import uuid


class CommunicationResponse(BaseModel):
    id: uuid.UUID
    channel: str
    sender: str
    recipients: List[str]
    subject: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)


