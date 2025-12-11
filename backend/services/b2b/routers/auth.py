from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from services.b2b.schemas import TenantResolutionRequest, TenantResolutionResponse, UserResponse
from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.user_service import user_service
from services.b2b.services.auth_provider_service import auth_provider_service
from services.b2b.services.rls_service import rls_service
from core.utils.firebase import firebase_auth_service
from services.b2b.models import InvitationModel
from core.middleware import get_current_user
from core.database import get_db
from core.constants import B2BRoleName

# Import structured logging
from core.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


router = APIRouter(prefix="/api/b2b/auth", tags=["authentication"])


# Mobile-specific schemas
class MobileLoginRequest(BaseModel):
    """Request model for mobile OAuth token exchange"""
    oidc_id_token: str
    email: EmailStr
    firebase_tenant_id: str
    provider_id: str  # e.g., 'oidc.auth0-mycompany'

@router.post("/mobile-login")
async def mobile_login(
    request: MobileLoginRequest,
    db: AsyncSession = Depends(get_db)):
    """
    Exchange OIDC ID token for Firebase ID token using GCIP signInWithIdp
    
    This performs a server-side token exchange with Google Identity Platform.
    It returns a standard Firebase ID Token (not custom token) which ensures
    stable UIDs across Web and Mobile.
    """
    logger.info("mobile_login_started", 
                email=request.email, 
                firebase_tenant_id=request.firebase_tenant_id,
                provider_id=request.provider_id)
    
    # 1. Get API Key from config
    from core.config import settings
    api_key = settings.firebase_api_key
    
    if not api_key:
        logger.error("missing_firebase_api_key")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Missing Firebase Web API Key"
        )
        
    # 2. Call Google Identity Toolkit API
    import httpx
    
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={api_key}"
    
    # Construct postBody for generic OIDC provider
    # Format: id_token=[ID_TOKEN]&providerId=[PROVIDER_ID]
    post_body = f"id_token={request.oidc_id_token}&providerId={request.provider_id}"
    
    payload = {
        "postBody": post_body,
        "requestUri": "http://localhost:3000/auth/callback",  # Dummy URI required by API
        "returnIdpCredential": True,
        "returnSecureToken": True,
        "tenantId": request.firebase_tenant_id
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                logger.warning("gcip_signin_failed", status=response.status_code, error=error_msg)
                
                # Map specific GCIP errors to HTTP exceptions
                if "INVALID_ID_TOKEN" in error_msg:
                    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid OIDC ID Token")
                elif "EMAIL_EXISTS" in error_msg:
                     # This happens if account linking is required but not handled here
                     # For B2B SSO, emails should match and link automatically
                     raise HTTPException(status.HTTP_409_CONFLICT, "Account linking required")
                else:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Login failed: {error_msg}")
            
            data = response.json()
            
            # 3. Extract tokens
            firebase_id_token = data.get('idToken')
            firebase_uid = data.get('localId')
            refresh_token = data.get('refreshToken')
            expires_in = data.get('expiresIn', '3600')
            
            logger.info("mobile_login_successful", 
                        email=request.email, 
                        firebase_uid=firebase_uid)
            
            # 4. Resolve Tenant (for correct return format)
            tenant = await tenant_service.get_tenant_by_firebase_id(db, request.firebase_tenant_id)
            
            if not tenant:
                 # Should theoretically not happen if GCIP accepted tenantId
                logger.error("tenant_not_found_after_gcip", tenant_id=request.firebase_tenant_id)
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant context lost")

            return {
                "firebase_id_token": firebase_id_token,
                "firebase_uid": firebase_uid,
                "refresh_token": refresh_token,
                "expires_in": int(expires_in),
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name
            }
            
    except httpx.RequestError as e:
        logger.error("gcip_network_error", error=str(e))
        raise HTTPException(
            detail="Authentication service unavailable"
        )

class OIDCConfigResponse(BaseModel):
    """OIDC configuration for mobile app"""
    issuer: str
    client_id: str
    scopes: list[str]



@router.post("/resolve-tenant", response_model=TenantResolutionResponse)
async def resolve_tenant(request: TenantResolutionRequest, db: AsyncSession = Depends(get_db)):
    """
    Resolve tenant from email address
    
    This endpoint extracts the domain from the email and looks up
    the corresponding tenant, returning the Firebase tenant ID that
    the frontend needs to set the auth context.
    """
    logger.info("tenant_resolution_started", email=request.email)
    
    # Extract domain from email
    domain = tenant_service.extract_domain_from_email(request.email)
    
    if not domain:
        logger.warning("invalid_email_format", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email address"
        )
    
    logger.debug("domain_extracted", domain=domain, email=request.email)
    
    # Look up tenant by domain
    tenant = await tenant_service.get_tenant_by_domain(db, domain)
    
    if not tenant:
        logger.warning("tenant_not_found", domain=domain, email=request.email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tenant found for domain: {domain}"
        )
    
    # Get primary auth provider
    primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
    
    logger.info("tenant_resolved",
                tenant_id=str(tenant.id),
                tenant_name=tenant.name,
                domain=domain,
                has_auth_provider=primary_provider is not None)
    
    return TenantResolutionResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        domain=tenant.domain,
        firebase_tenant_id=tenant.firebase_tenant_id,
        oidc_provider_id=primary_provider.provider_id if primary_provider else None
    )


@router.get("/oidc-config/{provider_id}", response_model=OIDCConfigResponse)
async def get_oidc_config(provider_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get OIDC configuration for mobile authentication
    
    Returns the issuer URL, client ID, and scopes needed for
    react-native-app-auth to perform OAuth flow.
    """
    logger.info("oidc_config_requested", provider_id=provider_id)
    
    # Get auth provider by provider_id (string identifier like 'oidc.auth0-firstcompany')
    from services.b2b.models.auth_provider import AuthProvider
    result = await db.execute(
        select(AuthProvider)
        .where(AuthProvider.provider_id == provider_id)
        .where(AuthProvider.is_active == True)
        .where(AuthProvider.deleted_at.is_(None))
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        logger.warning("oidc_provider_not_found", provider_id=provider_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OIDC provider not found: {provider_id}"
        )
    
    logger.info("oidc_config_retrieved", 
                provider_id=provider_id,
                provider_type=provider.provider_type)
    
    # Extract OIDC config from config_data JSONB
    config = provider.config_data or {}
    issuer_url = config.get('issuer_url') or config.get('issuer')
    client_id = config.get('client_id')
    
    if not issuer_url or not client_id:
        logger.error("oidc_config_incomplete", 
                    provider_id=provider_id,
                    has_issuer=bool(issuer_url),
                    has_client_id=bool(client_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OIDC provider configuration incomplete"
        )
    
    return OIDCConfigResponse(
        issuer=issuer_url,
        client_id=config.get('mobile_client_id') or client_id,  # Prefer mobile-specific client ID
        scopes=['openid', 'profile', 'email']
    )





@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """
    Get current authenticated user
    
    This endpoint validates the Firebase ID token and returns or creates
    the user record in PostgreSQL.
    """
    # Extract user info from token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    if not firebase_uid or not email or not firebase_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing required claims"
        )
    
    # Get tenant from Firebase tenant ID
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found for Firebase tenant: {firebase_tenant_id}"
        )
    
    # Set RLS Context for this request
    await rls_service.set_tenant_context(db, tenant.id)
    
    # Determine role from invitation (for new users)
    result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == tenant.id)
        .where(InvitationModel.email == email.lower())
    )
    invitation = result.scalar_one_or_none()
    user_role = invitation.role if invitation else B2BRoleName.VIEWER
    
    # Use email-based identity lookup (industry standard for cross-platform)
    # This ensures web and mobile users are recognized as the same person
    user = await user_service.get_or_create_user_by_email(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,  # Slug (e.g., 'admin')
        role_display_name=user.role_display_name,
        tenant_id=tenant.id,
        tenant_name=tenant.name
    )


@router.post("/sync-user")
async def sync_user(
    background_tasks: BackgroundTasks,
    request: Request,
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)):
    """
    Sync user with database after authentication
    
    This is called by the frontend after successful SSO login
    to ensure user exists in our database.
    """
    # Extract user info from token
    user_info = firebase_auth_service.get_user_info(decoded_token)
    
    firebase_uid = user_info.get("firebase_uid")
    email = user_info.get("email")
    name = user_info.get("name")
    firebase_tenant_id = user_info.get("firebase_tenant_id")
    
    if not firebase_uid or not email or not firebase_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing required claims"
        )
    
    # Get tenant from Firebase tenant ID
    tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found for Firebase tenant: {firebase_tenant_id}"
        )
    
    # Set RLS Context for this request
    await rls_service.set_tenant_context(db, tenant.id)
    
    # Determine role from invitation (for new users)
    result = await db.execute(
        select(InvitationModel)
        .where(InvitationModel.tenant_id == tenant.id)
        .where(InvitationModel.email == email.lower())
    )
    invitation = result.scalar_one_or_none()
    user_role = invitation.role if invitation else B2BRoleName.VIEWER
    
    # Use email-based identity lookup (industry standard for cross-platform)
    user = await user_service.get_or_create_user_by_email(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role
    )
    
    # Synchronous Audit Log (Unit of Work Pattern)
    # This uses the SAME db session and transaction.
    # It will be committed automatically when the request ends successfully.
    from services.b2b.services.audit_service import AuditService
    audit_service = AuditService(db)
    
    await audit_service.log_event(
        tenant_id=tenant.id,
        event_type="auth.login",
        resource_type="user",
        actor_id=user.id,
        resource_id=user.id,
        details={"email": email, "method": "sso_sync"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    
    return {
        "message": "User synced successfully",
        "user_id": user.id,
        "email": user.email,
        "role": user.role,  # Slug
        "role_display_name": user.role_display_name
    }
