"""
Pydantic schemas for Farmer Management API
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FarmerCreate(BaseModel):
    """Request to create a new farmer"""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1234567890",
                "address": "123 Farm Road, Village"
            }
        }


class FarmerUpdate(BaseModel):
    """Request to update farmer details"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class FarmerResponse(BaseModel):
    """Farmer details response"""
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
