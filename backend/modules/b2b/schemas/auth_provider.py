"""
Auth Provider Schemas (DTOs) for B2B tenants
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class AuthProviderType(str, Enum):
    """Supported authentication provider types"""
    OIDC = "oidc"
    SAML = "saml"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    AZURE_AD = "azure_ad"

class AuthProviderBase(BaseModel):
    """Base schema for auth provider"""
    provider_type: AuthProviderType
    provider_id: str = Field(..., max_length=255, description="Firebase provider identifier (e.g., 'oidc.auth0')")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    is_primary: bool = Field(False, description="Primary authentication provider for this tenant")
    is_active: bool = Field(True, description="Whether this provider is active")
    config_data: Optional[Dict[str, Any]] = Field(None, description="Additional provider-specific configuration")

class AuthProviderCreate(AuthProviderBase):
    """Schema for creating a new auth provider"""
    tenant_id: UUID

class AuthProviderUpdate(BaseModel):
    """Schema for updating an auth provider"""
    display_name: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    config_data: Optional[Dict[str, Any]] = None

class AuthProviderResponse(AuthProviderBase):
    """Schema for auth provider response"""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AuthProviderListResponse(BaseModel):
    """Schema for listing auth providers"""
    providers: list[AuthProviderResponse]
    total: int
