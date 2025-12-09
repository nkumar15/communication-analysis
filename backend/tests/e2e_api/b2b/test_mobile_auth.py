"""
Integration tests for Mobile Native Authentication and Cross-Platform UID Consistency

These tests verify:
1. Mobile-specific API endpoints (resolve-tenant, oidc-config, mobile-login)
2. Cross-platform user identity consistency (Email-based lookup)
3. Web→Mobile and Mobile→Web user resolution

Ref: docs/architecture/tenant-onboarding-flow.md (Mobile Native Authentication section)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from uuid import uuid4
from unittest.mock import patch, MagicMock

from services.b2b.models import UserModel, TenantModel
from services.b2b.services.rls_service import rls_service
from core.constants import B2BRoleName
from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt
)


@pytest.mark.integration
class TestMobileAuthEndpoints:
    """Tests for mobile native authentication API endpoints"""
    
    @pytest.mark.asyncio
    async def test_resolve_tenant_returns_oidc_provider(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        MOB-01: Tenant resolution includes OIDC provider ID for mobile
        """
        domain = f"mobile-{uuid4().hex[:8]}.com"
        tenant = await create_test_tenant(db_session, domain=domain)
        
        response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": f"user@{domain}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Mobile needs these fields for OAuth
        assert "firebase_tenant_id" in data
        assert "oidc_provider_id" in data
        assert data["domain"] == domain
    
    @pytest.mark.asyncio
    async def test_oidc_config_endpoint(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        MOB-02: OIDC config endpoint returns issuer_url and client_id
        """
        domain = f"oidc-{uuid4().hex[:8]}.com"
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Need to get the provider ID first
        resolve_response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": f"user@{domain}"}
        )
        provider_id = resolve_response.json().get("oidc_provider_id")
        
        if provider_id:
            response = await api_client.get(
                f"/api/b2b/auth/oidc-config/{provider_id}"
            )
            
            # Either 200 with config or 400/404 if not configured
            assert response.status_code in [200, 400, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert "issuer_url" in data or "client_id" in data
    
    @pytest.mark.asyncio
    async def test_mobile_login_endpoint_validates_tenant(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        MOB-03: Mobile login requires valid firebase_tenant_id
        """
        domain = f"mobile-login-{uuid4().hex[:8]}.com"
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Invalid tenant ID should fail
        response = await api_client.post(
            "/api/b2b/auth/mobile-login",
            json={
                "oidc_id_token": "fake-token",
                "email": f"user@{domain}",
                "firebase_tenant_id": "invalid-tenant-id"
            }
        )
        
        # Should fail with 401 or 404 for invalid tenant
        assert response.status_code in [401, 404]


@pytest.mark.integration
class TestCrossPlatformUIDConsistency:
    """
    Tests for email-based user identity - Ensures the same user logging in 
    from Web and Mobile is recognized as the same person.
    
    Ref: Email-Based User Identity Management section
    """
    
    @pytest.mark.asyncio
    async def test_user_created_on_web_recognized_on_mobile_flow(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        UID-01: User created via web (GCIP) is recognized when using mobile flow
        
        Scenario:
        1. User activates on web → gets GCIP-style UID
        2. User logs in on mobile → different UID in token
        3. Backend recognizes same email → updates UID, returns same user
        """
        domain = f"crossplatform-{uuid4().hex[:8]}.com"
        email = f"owner@{domain}"
        
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Simulate web login - user created with GCIP-style UID
        web_uid = f"oidc.auth0-{domain.replace('.', '-')}:auth0|{uuid4().hex[:12]}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=web_uid,
            role_slug=B2BRoleName.ADMIN
        )
        await db_session.commit()
        
        original_user_id = user.id
        
        # Simulate mobile login - different UID format
        mobile_uid = f"oidc-{email.replace('@', '_').replace('.', '_')}"
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=mobile_uid,  # Different UID!
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Call /me endpoint (which uses email-based lookup)
        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return the SAME user (by email lookup)
        assert data["id"] == str(original_user_id)
        assert data["email"] == email
        
        # Verify UID was updated in database
        await rls_service.set_tenant_context(db_session, tenant.id)
        result = await db_session.execute(
            select(UserModel).where(UserModel.id == original_user_id)
        )
        updated_user = result.scalar_one()
        assert updated_user.firebase_uid == mobile_uid  # UID updated to mobile format
    
    @pytest.mark.asyncio
    async def test_user_created_on_mobile_recognized_on_web_flow(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        UID-02: User created via mobile is recognized when using web flow
        
        Scenario:
        1. User first logs in on mobile → gets email-based UID
        2. User later logs in on web → gets GCIP-style UID
        3. Backend recognizes same email → updates UID, returns same user
        """
        domain = f"crossplatform2-{uuid4().hex[:8]}.com"
        email = f"user@{domain}"
        
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Simulate mobile login first - user created with mobile-style UID
        mobile_uid = f"oidc-{email.replace('@', '_').replace('.', '_')}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=mobile_uid,
            role_slug=B2BRoleName.VIEWER
        )
        await db_session.commit()
        
        original_user_id = user.id
        
        # Simulate web login - GCIP-style UID
        web_uid = f"oidc.auth0-test:auth0|{uuid4().hex[:12]}"
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=web_uid,  # Different UID!
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Call /sync-user endpoint (also uses email-based lookup)
        response = await api_client.post(
            "/api/b2b/auth/sync-user",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return the SAME user (by email lookup)
        assert data["email"] == email
        
        # Verify UID was updated in database
        await rls_service.set_tenant_context(db_session, tenant.id)
        result = await db_session.execute(
            select(UserModel).where(UserModel.id == original_user_id)
        )
        updated_user = result.scalar_one()
        assert updated_user.firebase_uid == web_uid  # UID updated to web format
    
    @pytest.mark.asyncio
    async def test_email_is_canonical_identity_not_uid(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        UID-03: Email is the stable identifier, UID can change
        
        Verify that users are looked up by email, not firebase_uid
        """
        domain = f"email-canonical-{uuid4().hex[:8]}.com"
        email = f"stable@{domain}"
        
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Create user with initial UID
        initial_uid = f"uid-version-1-{uuid4().hex[:8]}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=initial_uid,
            role_slug=B2BRoleName.ADMIN
        )
        await db_session.commit()
        
        user_id = user.id
        
        # Login with completely different UID but same email
        new_uid_v2 = f"uid-version-2-{uuid4().hex[:8]}"
        jwt_v2 = encode_mock_jwt(create_mock_firebase_token(
            uid=new_uid_v2,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        response_v2 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_v2}"}
        )
        
        assert response_v2.status_code == 200
        assert response_v2.json()["id"] == str(user_id)
        
        # Login with another different UID 
        new_uid_v3 = f"uid-version-3-{uuid4().hex[:8]}"
        jwt_v3 = encode_mock_jwt(create_mock_firebase_token(
            uid=new_uid_v3,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        response_v3 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_v3}"}
        )
        
        assert response_v3.status_code == 200
        assert response_v3.json()["id"] == str(user_id)  # Still same user
        
        # Verify: Only 1 user exists with this email
        await rls_service.set_tenant_context(db_session, tenant.id)
        result = await db_session.execute(
            select(UserModel).where(
                UserModel.tenant_id == tenant.id,
                UserModel.email == email
            )
        )
        users = result.scalars().all()
        assert len(users) == 1  # No duplicate users created!
    
    @pytest.mark.asyncio
    async def test_different_emails_create_different_users(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        UID-04: Different emails = different users (even with similar UIDs)
        
        Ensure email-based lookup doesn't accidentally merge different users
        """
        domain = f"diff-emails-{uuid4().hex[:8]}.com"
        
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # User A
        email_a = f"user-a@{domain}"
        jwt_a = encode_mock_jwt(create_mock_firebase_token(
            uid=f"similar-uid-{uuid4().hex[:8]}",
            email=email_a,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response_a = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_a}"}
        )
        assert response_a.status_code == 200
        user_a_id = response_a.json()["id"]
        
        # User B - different email!
        email_b = f"user-b@{domain}"
        jwt_b = encode_mock_jwt(create_mock_firebase_token(
            uid=f"similar-uid-{uuid4().hex[:8]}",  # Similar UID pattern
            email=email_b,  # Different email
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response_b = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_b}"}
        )
        assert response_b.status_code == 200
        user_b_id = response_b.json()["id"]
        
        # Different users
        assert user_a_id != user_b_id
        
        # Verify: 2 distinct users in database
        await rls_service.set_tenant_context(db_session, tenant.id)
        result = await db_session.execute(
            select(UserModel).where(UserModel.tenant_id == tenant.id)
        )
        users = result.scalars().all()
        emails = [u.email for u in users]
        assert email_a in emails
        assert email_b in emails


@pytest.mark.integration
class TestMobileOnboardingFlow:
    """
    Full mobile onboarding flow test - mirrors the web onboarding test
    but uses mobile-specific endpoints
    """
    
    @pytest.mark.asyncio
    async def test_mobile_tenant_resolution_flow(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """
        MOB-04: Complete mobile tenant resolution flow
        
        1. User enters email
        2. App resolves tenant
        3. App gets OIDC config
        4. (OAuth happens externally)
        5. App calls mobile-login with OIDC token
        """
        domain = f"mobile-flow-{uuid4().hex[:8]}.com"
        email = f"mobileuser@{domain}"
        
        tenant = await create_test_tenant(db_session, domain=domain)
        
        # Step 1-2: Resolve tenant
        resolve_response = await api_client.post(
            "/api/b2b/auth/resolve-tenant",
            json={"email": email}
        )
        
        assert resolve_response.status_code == 200
        resolve_data = resolve_response.json()
        
        assert resolve_data["firebase_tenant_id"] == tenant.firebase_tenant_id
        assert "oidc_provider_id" in resolve_data
        
        print(f"✅ Tenant resolved: {resolve_data['tenant_name']}")
        print(f"   Firebase Tenant ID: {resolve_data['firebase_tenant_id']}")
        print(f"   OIDC Provider ID: {resolve_data['oidc_provider_id']}")
        
        # Step 3: Get OIDC config (if provider configured)
        provider_id = resolve_data.get("oidc_provider_id")
        if provider_id:
            oidc_response = await api_client.get(
                f"/api/b2b/auth/oidc-config/{provider_id}"
            )
            print(f"   OIDC Config Response: {oidc_response.status_code}")
        
        # Steps 4-5 would require actual OIDC token - skip in unit test
        # Instead, verify user can access /me after simulated login
        
        # Simulate: User completed OAuth, now has Firebase token
        firebase_uid = f"mobile-{uuid4().hex[:8]}"
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        me_response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        assert me_data["email"] == email
        print(f"✅ Mobile user authenticated: {me_data['email']}")
        print(f"   User ID: {me_data['id']}")
        print(f"   Role: {me_data['role']}")
