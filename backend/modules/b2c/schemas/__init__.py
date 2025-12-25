from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Dict, Any

class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str
    type: str  # 'personal' or 'team'

class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace"""
    pass

class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response"""
    id: UUID4
    owner_id: UUID4
    subscription_tier: str
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class B2CUserResponse(BaseModel):
    """Schema for B2C user response"""
    id: UUID4
    email: str
    display_name: Optional[str]
    default_workspace_id: Optional[UUID4]
    created_at: datetime
    
    class Config:
        from_attributes = True
