from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class CaseNoteBase(BaseModel):
    content: str
    author_id: Optional[uuid.UUID] = None

class CaseNoteCreate(CaseNoteBase):
    pass

class CaseNoteResponse(CaseNoteBase):
    id: uuid.UUID
    case_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class CaseEvidenceBase(BaseModel):
    evidence_type: str # 'communication', 'alert'
    evidence_id: uuid.UUID
    notes: Optional[str] = None

class CaseEvidenceCreate(CaseEvidenceBase):
    pass

class CaseEvidenceResponse(CaseEvidenceBase):
    id: uuid.UUID
    case_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class CaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    priority: str = "medium"
    status: str = "open"
    target_closure_date: Optional[datetime] = None

class CaseCreate(CaseBase):
    """Payload to create a new case, optionally with initial evidence."""
    assigned_to_user_id: Optional[uuid.UUID] = None
    data_region_id: Optional[uuid.UUID] = None
    sensitivity_level_id: Optional[uuid.UUID] = None
    initial_note: Optional[str] = None
    initial_evidence: Optional[List[CaseEvidenceCreate]] = None

class CaseUpdate(BaseModel):
    """Payload to update case metadata, status, or close it."""
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assigned_to_user_id: Optional[uuid.UUID] = None
    target_closure_date: Optional[datetime] = None
    decision_rationale: Optional[str] = None
    closed_at: Optional[datetime] = None

class CaseResponse(CaseBase):
    """Full case object with metadata and audit timestamps."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    assigned_to_user_id: Optional[uuid.UUID] = None
    decision_rationale: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Optional nested data for detail view
    notes: Optional[List[CaseNoteResponse]] = None
    evidence: Optional[List[CaseEvidenceResponse]] = None

    class Config:
        from_attributes = True
