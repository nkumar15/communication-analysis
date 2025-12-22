"""
Authentication Schemas

Schemas for B2B authentication workflows.
"""
from pydantic import BaseModel, EmailStr
from uuid import UUID


class MobileLoginRequest(BaseModel):
    """Request model for mobile OAuth token exchange"""
    oidc_id_token: str
    email: EmailStr
    firebase_tenant_id: str
    provider_id: str  # e.g., 'oidc.auth0-mycompany'
    nonce: str | None = None


class MobileLoginResponse(BaseModel):
    """Response from mobile login"""
    firebase_custom_token: str
    firebase_id_token: str
    firebase_uid: str
    refresh_token: str
    expires_in: int
    tenant_id: str
    tenant_name: str


class OIDCConfigResponse(BaseModel):
    """OIDC configuration for mobile app"""
    issuer: str
    client_id: str
    scopes: list[str]
