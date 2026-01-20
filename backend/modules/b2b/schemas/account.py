"""
Account Settings Schemas
"""
from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional


class AccountSettingsResponse(BaseModel):
    """Response model for account settings"""
    name: str
    domain: str  # Read-only
    logo_url: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AccountSettingsUpdate(BaseModel):
    """Request model for updating account settings"""
    name: Optional[str] = None
    logo_url: Optional[str] = None
