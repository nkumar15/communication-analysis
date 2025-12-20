"""
SSO Settings Schemas

Request/Response models for tenant SSO configuration management.
"""
from pydantic import BaseModel, Field
from typing import Optional


class SSOConfigResponse(BaseModel):
    """Current SSO configuration (safe for display)"""
    provider_type: str
    provider_id: str
    client_id: str
    client_id_masked: str  # "abc***xyz" for display
    issuer: str
    is_active: bool
    has_mobile: bool = False
    mobile_client_id: Optional[str] = None
    mobile_client_id_masked: Optional[str] = None


class SSOConfigUpdateRequest(BaseModel):
    """Request to update SSO configuration"""
    client_id: str = Field(..., min_length=1, description="OIDC Client ID")
    client_secret: str = Field(..., min_length=1, description="OIDC Client Secret")
    issuer: str = Field(..., min_length=1, description="OIDC Issuer URL")
    mobile_client_id: Optional[str] = Field(None, description="Mobile OIDC Client ID (optional)")
    mobile_client_secret: Optional[str] = Field(None, description="Mobile OIDC Client Secret (optional)")


class SSOConfigUpdateResponse(BaseModel):
    """Response after updating SSO config"""
    success: bool
    message: str = "SSO configuration updated successfully"

