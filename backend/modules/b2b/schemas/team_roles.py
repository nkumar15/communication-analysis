from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TeamRoleCreate(BaseModel):
    """Create team role request"""
    name: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z_]+$')
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: List[dict] = []
    is_default: bool = False


class TeamRoleUpdate(BaseModel):
    """Update team role request"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[dict]] = None
    is_default: Optional[bool] = None


class TeamRoleResponse(BaseModel):
    """Team role response"""
    id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[dict] = []
    is_system: bool
    is_default: bool
    
    model_config = ConfigDict(from_attributes=True)
