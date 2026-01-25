from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from modules.domains.b2b.bank_surveillance.models.alert import AlertStatus, AlertSeverity, RiskType

class AlertBase(BaseModel):
    risk_type: Optional[RiskType] = None
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    description: Optional[str] = None
    metadata_: Dict[str, Any] = Field(
        default={}, 
        validation_alias=AliasChoices("metadata_", "metadata"), 
        serialization_alias="metadata"
    )

class AlertCreate(AlertBase):
    tenant_id: UUID
    communication_id: UUID
    assigned_to: Optional[UUID] = None
    detected_at: Optional[datetime] = None

class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    assigned_to: Optional[UUID] = None
    description: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = Field(
        default=None, 
        validation_alias=AliasChoices("metadata_", "metadata"), 
        serialization_alias="metadata"
    )

class AlertFilter(BaseModel):
    status: Optional[AlertStatus] = None
    severity: Optional[AlertSeverity] = None
    risk_type: Optional[RiskType] = None
    assigned_to: Optional[UUID] = None
    communication_id: Optional[UUID] = None
    region: Optional[str] = None

class AlertStats(BaseModel):
    total_alerts: int
    high_risk_count: int
    open_count: int
    unassigned_count: int

class ThreadMessage(BaseModel):
    id: UUID
    sender: str
    subject: Optional[str] = None
    content: Optional[str] = None
    timestamp: datetime
    is_trigger: bool = False
    risk_indicators: List[str] = []
    matched_keywords: List[str] = []

class AlertResponse(AlertBase):
    id: UUID
    tenant_id: UUID
    communication_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    assignee_name: Optional[str] = None
    detected_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Context
    region: Optional[str] = None
    conversation_thread: List[ThreadMessage] = []

    model_config = ConfigDict(from_attributes=True)
