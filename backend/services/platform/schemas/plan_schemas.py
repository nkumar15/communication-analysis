"""
Subscription Plan Schemas for Platform API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class PlanBase(BaseModel):
    tier_key: str = Field(..., description="Logical identifier for the plan tier (e.g. 'premium')")
    name: str = Field(..., description="Display name of the plan")
    description: Optional[str] = None
    price_monthly: Optional[int] = Field(None, description="Monthly price in cents")
    price_yearly: Optional[int] = Field(None, description="Yearly price in cents")
    provider_config: Dict[str, Any] = Field(default_factory=dict, description="Provider specific config (stripe price IDs)")
    limits: Dict[str, Any] = Field(default_factory=dict, description="Usage limits")
    features: Dict[str, Any] = Field(default_factory=dict, description="Feature flags")

class PlanCreate(PlanBase):
    effective_from: Optional[datetime] = None

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[int] = None
    price_yearly: Optional[int] = None
    provider_config: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    # Note: tier_key cannot be changed easily as it links versions. 
    # To change tier_key, create new plan.

class PlanResponse(PlanBase):
    id: UUID
    tier_key: str
    effective_from: datetime
    archived_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[UUID]

    class Config:
        from_attributes = True
