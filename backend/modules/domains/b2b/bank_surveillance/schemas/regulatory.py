from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RegulatoryDocumentBase(BaseModel):
    title: str
    framework: Optional[str] = None
    region_id: Optional[UUID] = None
    year: Optional[int] = None
    version: Optional[str] = None
    storage_path: Optional[str] = None

class RegulatoryDocumentCreate(RegulatoryDocumentBase):
    tenant_id: UUID

class RegulatoryDocumentUpdate(BaseModel):
    title: Optional[str] = None
    framework: Optional[str] = None
    region_id: Optional[UUID] = None
    year: Optional[int] = None
    version: Optional[str] = None
    storage_path: Optional[str] = None

class RegulatoryDocumentResponse(RegulatoryDocumentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
