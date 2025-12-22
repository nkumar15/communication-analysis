from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class AuditLogResponse(BaseModel):
    id: UUID
    event_type: str
    resource_type: str
    resource_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditLogList(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    limit: int
