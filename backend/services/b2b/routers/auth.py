from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from services.b2b.schemas import TenantResolutionRequest, TenantResolutionResponse, UserResponse
from services.b2b.services.tenant_service import tenant_service
from services.b2b.services.user_service import user_service
from services.b2b.services.auth_provider_service import auth_provider_service
from services.b2b.services.audit_service import log_audit_background
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



@router.post("/mobile-login")
async def mobile_login(
    request: MobileLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange OIDC ID token for Firebase custom token (Mobile OAuth flow)
    
    Flow:
    1. Decode & validate OIDC ID token
    2. Verify tenant and email
    3. Generate Firebase custom token for that tenant
    4. Return custom token to mobile app
    
    The mobile app will then use signInWithCustomToken() to authenticate.
    """
    logger.info("mobile_login_started", email=request.email, firebase_tenant_id=request.firebase_tenant_id)
    
    # Get auth provider to retrieve issuer for JWT verification
    # Extract provider ID from request if needed, or look it up
    tenant = await tenant_service.get_tenant_by_firebase_id(db, request.firebase_tenant_id)
    
    if not tenant:
        logger.warning("tenant_not_found", firebase_tenant_id=request.firebase_tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get primary auth provider for this tenant
    primary_provider = await auth_provider_service.get_primary_provider(db, tenant.id)
    
    if not primary_provider:
        logger.warning("no_auth_provider", tenant_id=str(tenant.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authentication provider configured for this tenant"
        )
    
    try:
        # 1. Verify and decode OIDC token with signature validation
        import jwt
        from jwt import PyJWKClient
        
        # Get JWKS URL from issuer (standard OIDC discovery)
        issuer = primary_provider.oidc_issuer_url.rstrip('/')
        jwks_url = f"{issuer}/.well-known/jwks.json"
        
        logger.debug("fetching_jwks", jwks_url=jwks_url)
        
        # Fetch and cache public keys
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(request.oidc_id_token)
        
        # Verify signature and decode
        decoded = jwt.decode(
            request.oidc_id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=primary_provider.oidc_client_id_mobile or primary_provider.oidc_client_id,
            issuer=issuer,
        )
        
        oidc_email = decoded.get('email')
        
        if not oidc_email:
            logger.warning("oidc_token_missing_email")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OIDC token missing email claim"
            )
        
        logger.debug("oidc_token_verified", oidc_email=oidc_email)
        
    except jwt.ExpiredSignatureError:
        logger.warning("oidc_token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC token has expired"
        )
    except jwt.InvalidAudienceError:
        logger.warning("oidc_token_invalid_audience")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC token audience mismatch"
        )
    except jwt.InvalidIssuerError:
        logger.warning("oidc_token_invalid_issuer")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC token issuer mismatch"
        )
    except jwt.DecodeError as e:
        logger.warning("oidc_token_invalid", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OIDC token: {str(e)}"
        )
    except Exception as e:
        logger.error("oidc_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )
    
    # 2. Verify email matches
    if oidc_email.lower() != request.email.lower():
        logger.warning("email_mismatch", oidc_email=oidc_email, request_email=request.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email mismatch between token and request"
    )
    
    # 3. Verify tenant is active (already fetched above)
    
    if tenant.activation_status != 'active':
        logger.warning("tenant_not_active", tenant_id=str(tenant.id), status=tenant.activation_status)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active"
        )
    
    # 4. Generate Firebase UID (deterministic based on email)
    # This ensures same user gets same UID across sessions
    firebase_uid = f"oidc-{oidc_email.replace('@', '_').replace('.', '_')}"
    
    logger.debug("generating_firebase_token", firebase_uid=firebase_uid, tenant_id=str(tenant.id))
    
    # 5. Create Firebase custom token for this tenant
    try:
        custom_token = firebase_auth_service.create_custom_token(
            uid=firebase_uid,
            tenant_id=request.firebase_tenant_id,
            claims={'email': oidc_email}
        )
        
        logger.info("mobile_login_successful",
                   email=oidc_email,
                   tenant_id=str(tenant.id),
                   firebase_tenant_id=request.firebase_tenant_id)
        
        return {
            "firebase_custom_token": custom_token.decode('utf-8'),
            "firebase_uid": firebase_uid,
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name
        }
        
    except Exception as e:
        logger.error("firebase_token_generation_failed", error=str(e), firebase_uid=firebase_uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Firebase token: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    decoded_token: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
    
    
    # Check if user already exists by Firebase UID OR by email
    existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    # If not found by UID, check by email (for users created with temporary UIDs)
    if not existing_user:
        from services.b2b.models import UserModel
        result = await db.execute(
            select(UserModel)
            .where(UserModel.tenant_id == tenant.id)
            .where(UserModel.email == email.lower())
            .where(UserModel.is_active == True)
        )
        existing_user_by_email = result.scalar_one_or_none()
        
        if existing_user_by_email:
            # Update Firebase UID if it's a temporary one (starts with "oidc-")
            if existing_user_by_email.firebase_uid.startswith('oidc-'):
                existing_user_by_email.firebase_uid = firebase_uid
                # Flush, re-query with RLS context (FastAPI commits on success)
                await db.flush()
                result = await db.execute(
                    select(UserModel).where(UserModel.id == existing_user_by_email.id)
                )
                existing_user_by_email = result.scalar_one()
            existing_user = await user_service._model_to_pydantic(existing_user_by_email, db)
    
    if existing_user:
        # User exists, use default role (it won't overwrite existing role_id)
        user_role = B2BRoleName.VIEWER
    else:
        # New user, check invitation (including accepted ones for initial role assignment)
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant.id)
            .where(InvitationModel.email == email.lower())
        )
        invitation = result.scalar_one_or_none()
        
        # Use role from invitation if exists, otherwise default to 'viewer'
        user_role = invitation.role if invitation else B2BRoleName.VIEWER
    
    # Create or update user
    user = await user_service.create_or_update_user(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role  # Use determined role
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
    db: AsyncSession = Depends(get_db)
):
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
    
    # Check if user already exists to preserve their role
    existing_user = await user_service.get_user_by_firebase_uid(db, tenant.id, firebase_uid)
    
    if existing_user:
        # User exists, use default role (it won't overwrite existing role_id)
        user_role = B2BRoleName.VIEWER
    else:
        # New user, check invitation (including accepted ones for initial role assignment)
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant.id)
            .where(InvitationModel.email == email.lower())
        )
        invitation = result.scalar_one_or_none()
        
        # Use role from invitation if exists, otherwise default to 'viewer'
        user_role = invitation.role if invitation else B2BRoleName.VIEWER   
    
    # Create or update user
    user = await user_service.create_or_update_user(
        db=db,
        tenant_id=tenant.id,
        email=email,
        firebase_uid=firebase_uid,
        name=name,
        role=user_role  # Use determined role
    )
    
    # Log audit event
    background_tasks.add_task(
        log_audit_background,
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
