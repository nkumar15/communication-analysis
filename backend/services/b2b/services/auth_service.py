"""
Authentication Service

Handles OAuth flows, mobile login, and user synchronization.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Service for authentication operations"""
    
    async def mobile_login_exchange(
        self,
        db: AsyncSession,
        oidc_id_token: str,
        email: str,
        firebase_tenant_id: str,
        provider_id: str,
        nonce: Optional[str] = None
    ) -> dict:
        """
        Exchange OIDC ID token for Firebase custom token via GCIP
        
        Returns dict with custom_token, id_token, uid, refresh_token, etc.
        Raises HTTPException on failure
        """
        from fastapi import HTTPException, status
        from core.config import settings
        from services.b2b.services.tenant_service import tenant_service
        from core.utils.firebase import firebase_auth_service
        import httpx
        
        logger.info("mobile_login_started", 
                    email=email, 
                    firebase_tenant_id=firebase_tenant_id,
                    provider_id=provider_id)
        
        # 1. Get API Key from config
        api_key = settings.firebase_api_key
        
        if not api_key:
            logger.error("missing_firebase_api_key")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: Missing Firebase Web API Key"
            )
        
        # 2. Call Google Identity Toolkit API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={api_key}"
        
        # Construct postBody for generic OIDC provider
        post_body = f"id_token={oidc_id_token}&providerId={provider_id}"
        
        if nonce:
            post_body += f"&nonce={nonce}"
        
        payload = {
            "postBody": post_body,
            "requestUri": "http://localhost:3000/auth/callback",  # Dummy URI required by API
            "returnIdpCredential": True,
            "returnSecureToken": True,
            "tenantId": firebase_tenant_id
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
                            email=email, 
                            firebase_uid=firebase_uid)
                
                # 4. Resolve Tenant
                tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
                
                if not tenant:
                    logger.error("tenant_not_found_after_gcip", tenant_id=firebase_tenant_id)
                    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Tenant context lost")
                
                # 5. Create Custom Token for Client SDK
                custom_token_bytes = firebase_auth_service.create_custom_token(
                    uid=firebase_uid,
                    tenant_id=firebase_tenant_id
                )
                custom_token = custom_token_bytes.decode('utf-8')
                
                return {
                    "firebase_custom_token": custom_token,
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
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )
    
    async def resolve_tenant_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> dict:
        """
        Resolve tenant from email domain
        
        Returns dict with tenant info and auth provider
        Raises HTTPException if not found
        """
        from fastapi import HTTPException, status
        from services.b2b.services.tenant_service import tenant_service
        from services.b2b.services.auth_provider_service import auth_provider_service
        
        logger.info("tenant_resolution_started", email=email)
        
        # Extract domain from email
        domain = tenant_service.extract_domain_from_email(email)
        
        if not domain:
            logger.warning("invalid_email_format", email=email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address"
            )
        
        logger.debug("domain_extracted", domain=domain, email=email)
        
        # Look up tenant by domain
        tenant = await tenant_service.get_tenant_by_domain(db, domain)
        
        if not tenant:
            # Check if tenant exists but is deactivated
            deactivated_tenant = await tenant_service.get_tenant_by_domain_include_inactive(db, domain)
            if deactivated_tenant:
                logger.warning("tenant_deactivated", domain=domain, email=email)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This organization has been deactivated. Please contact your administrator."
                )
            
            logger.warning("tenant_not_found", domain=domain, email=email)
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
        
        # Get mobile specific provider ID if available
        mobile_provider_id = None
        if primary_provider and primary_provider.config_data:
            mobile_provider_id = primary_provider.config_data.get('mobile_provider_id')
        
        return {
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "domain": tenant.domain,
            "firebase_tenant_id": tenant.firebase_tenant_id,
            "oidc_provider_id": primary_provider.provider_id if primary_provider else None,
            "mobile_oidc_provider_id": mobile_provider_id,
            "provider_type": primary_provider.provider_type if primary_provider else 'oidc'
        }
    
    async def get_oidc_config(
        self,
        db: AsyncSession,
        provider_id: str
    ) -> dict:
        """
        Get OIDC configuration for mobile app
        
        Returns dict with issuer, client_id, scopes
        Raises HTTPException if not found or incomplete
        """
        from fastapi import HTTPException, status
        from services.b2b.models.auth_provider import AuthProvider
        
        logger.info("oidc_config_requested", provider_id=provider_id)
        
        # Get auth provider by provider_id
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
        
        return {
            "issuer": issuer_url,
            "client_id": config.get('mobile_client_id') or client_id,  # Prefer mobile-specific
            "scopes": ['openid', 'profile', 'email']
        }
    
    async def get_or_sync_user(
        self,
        db: AsyncSession,
        firebase_uid: str,
        email: str,
        name: Optional[str],
        firebase_tenant_id: str
    ) -> tuple:
        """
        Get or create user from Firebase token
        
        Returns tuple of (user, tenant, permissions, teams)
        Raises HTTPException on failure
        """
        from fastapi import HTTPException, status
        from services.b2b.services.tenant_service import tenant_service
        from services.b2b.services.user_service import user_service
        from services.b2b.models import InvitationModel
        from core.rls import rls_service
        from core.constants import B2BRoleName
        from services.b2b.rbac import get_user_permissions
        from services.b2b.models.team import Team
        from services.b2b.models.team_member import TeamMember
        
        # Get tenant from Firebase tenant ID
        tenant = await tenant_service.get_tenant_by_firebase_id(db, firebase_tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant not found for Firebase tenant: {firebase_tenant_id}"
            )
        
        # Set RLS Context
        await rls_service.set_tenant_context(db, tenant.id)
        
        # Determine role from invitation (for new users)
        result = await db.execute(
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant.id)
            .where(InvitationModel.email == email.lower())
        )
        invitation = result.scalar_one_or_none()
        user_role = invitation.role if invitation else B2BRoleName.VIEWER
        
        # Get or create user
        user = await user_service.get_or_create_user_by_email(
            db=db,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=firebase_uid,
            name=name,
            role=user_role
        )
        
        # Fetch permissions
        permissions = await get_user_permissions(user.id, db)
        
        # Fetch teams
        teams_result = await db.execute(
            select(Team.id, Team.name, TeamMember.team_role)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user.id)
            .where(Team.deleted_at.is_(None))
        )
        teams = [
            {"id": str(team_id), "name": name, "team_role": team_role}
            for team_id, name, team_role in teams_result.all()
        ]
        
        return user, tenant, permissions, teams


# Global auth service instance
auth_service = AuthService()
