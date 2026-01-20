from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from modules.domains.b2b.bank_surveillance.models.alert import AlertStatus, AlertSeverity, RiskType

class AlertBase(BaseModel):
    risk_type: RiskType
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

class AlertResponse(AlertBase):
    id: UUID
    tenant_id: UUID
    communication_id: UUID
    assigned_to: Optional[UUID]
    detected_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Optional nested details (could be expanded)
    # communication_summary: Optional[Dict] = None 

    model_config = ConfigDict(from_attributes=True)
