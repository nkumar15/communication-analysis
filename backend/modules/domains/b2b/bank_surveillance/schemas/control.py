from typing import Any, Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SurveillanceControlBase(BaseModel):
    risk_typology: str
    risk_indicator: str
    regulatory_id: Optional[UUID] = None
    regulatory_reference_text: Optional[str] = None
    detection_methods: List[Any] = []
    status: str = "Active"

class SurveillanceControlCreate(SurveillanceControlBase):
    tenant_id: UUID

class SurveillanceControlUpdate(BaseModel):
    risk_typology: Optional[str] = None
    risk_indicator: Optional[str] = None
    regulatory_id: Optional[UUID] = None
    regulatory_reference_text: Optional[str] = None
    detection_methods: Optional[List[Any]] = None
    status: Optional[str] = None

from .regulatory import RegulatoryDocumentResponse

class SurveillanceControlResponse(SurveillanceControlBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    regulatory_document: Optional[RegulatoryDocumentResponse] = None

    model_config = ConfigDict(from_attributes=True)
