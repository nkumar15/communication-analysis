"""
Integration tests for tenant deactivation and reactivation

Scope:
- Platform admin can deactivate active tenants
- Platform admin can reactivate deactivated tenants
- Deactivated tenant users are blocked from login
- Error cases (already active/inactive, not found)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from modules.b2b.models import TenantModel, UserModel
from core.db.rls import rls_service
from core.constants import B2BRoleName
from uuid import uuid4

from tests.conftest import (
    create_test_tenant,
    create_test_user,
    create_mock_firebase_token,
    encode_mock_jwt,
    platform_admin_setup
)


@pytest.mark.integration
class TestTenantDeactivation:
    """Test tenant deactivation by platform admin"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_can_deactivate_active_tenant(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that platform admin can deactivate an active tenant"""
        platform_admin_token = platform_admin_setup["token"]
        
        # Create active tenant
        tenant = await create_test_tenant(db_session, activation_status="active")
        await db_session.commit()
        
        # Deactivate tenant
        response = await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/deactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        
        # Verify tenant is now inactive
        await db_session.refresh(tenant)
        assert tenant.is_active is False
    
    @pytest.mark.asyncio
    async def test_deactivated_tenant_users_blocked_from_login(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        platform_admin_setup
    ):
        """Test that users from deactivated tenants cannot access APIs"""
        # Create active tenant with user
        tenant = await create_test_tenant(db_session, activation_status="active")
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        email = f"user@{tenant.domain}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Verify user can access API while tenant is active
        response1 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response1.status_code == 200
        
        # Deactivate tenant using Platform API
        platform_admin_token = platform_admin_setup["token"]
        response_deactivate = await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/deactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        assert response_deactivate.status_code == 200
        
        # Force SQLAlchemy to release cached objects so next request fetches fresh data
        # This is required because tests share the session between API calls
        db_session.expire_all()
        
        # Verify user is now blocked
        response2 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response2.status_code == 403
        assert "deactivated" in response2.json()["detail"].lower()
    

# ... (omitted methods)

@pytest.mark.integration
class TestTenantReactivation:
    # ... (omitted methods)
    
    @pytest.mark.asyncio
    async def test_reactivated_tenant_users_can_login_again(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession,
        platform_admin_setup
    ):
        """Test that users from reactivated tenants can access APIs again"""
        # Create user in active tenant first
        tenant = await create_test_tenant(db_session, activation_status="active")
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        email = f"user@{tenant.domain}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Verify access OK
        assert (await api_client.get("/api/b2b/auth/me", headers={"Authorization": f"Bearer {jwt}"})).status_code == 200

        # Deactivate tenant via API
        platform_admin_token = platform_admin_setup["token"]
        await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/deactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        db_session.expire_all()
        
        # Verify user is blocked
        response1 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response1.status_code == 403
        
        # Reactivate tenant via API
        await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/reactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        db_session.expire_all()
        
        # Verify user can now access API
        response2 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_tenant_returns_404(
        self,
        api_client: AsyncClient,
        platform_admin_setup
    ):
        """Test that deactivating non-existent tenant returns 404"""
        platform_admin_token = platform_admin_setup["token"]
        fake_tenant_id = uuid4()
        
        response = await api_client.patch(
            f"/api/platform/b2b/tenants/{fake_tenant_id}/deactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_tenant_list_shows_inactive_status_for_deactivated_tenants(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that tenant list API returns 'inactive' status for deactivated tenants"""
        platform_admin_token = platform_admin_setup["token"]
        
        # Create and deactivate tenant
        tenant = await create_test_tenant(db_session, activation_status="active")
        tenant.is_active = False
        await db_session.commit()
        
        # Get tenant list
        response = await api_client.get(
            "/api/platform/b2b/tenants",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Find our tenant in the list
        our_tenant = next((t for t in data["items"] if t["id"] == str(tenant.id)), None)
        assert our_tenant is not None
        assert our_tenant["status"] == "inactive"


@pytest.mark.integration
class TestTenantReactivation:
    """Test tenant reactivation by platform admin"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_can_reactivate_inactive_tenant(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that platform admin can reactivate a deactivated tenant"""
        platform_admin_token = platform_admin_setup["token"]
        
        # Create deactivated tenant
        tenant = await create_test_tenant(db_session, activation_status="active")
        tenant.is_active = False
        await db_session.commit()
        
        # Reactivate tenant
        response = await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/reactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(tenant.id)
        assert "reactivated" in data["message"].lower()
        
        # Verify tenant is now active
        await db_session.refresh(tenant)
        assert tenant.is_active is True
    
    @pytest.mark.asyncio
    async def test_reactivated_tenant_users_can_login_again(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that users from reactivated tenants can access APIs again"""
        # Create deactivated tenant with user
        tenant = await create_test_tenant(db_session, activation_status="active")
        tenant.is_active = False
        await rls_service.set_tenant_context(db_session, tenant.id)
        
        firebase_uid = f"firebase-{uuid4().hex[:8]}"
        email = f"user@{tenant.domain}"
        user = await create_test_user(
            db_session,
            tenant_id=tenant.id,
            email=email,
            firebase_uid=firebase_uid,
            role_slug=B2BRoleName.OWNER
        )
        await db_session.commit()
        
        jwt = encode_mock_jwt(create_mock_firebase_token(
            uid=firebase_uid,
            email=email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Verify user is blocked while tenant is inactive
        response1 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response1.status_code == 403
        
        # Reactivate tenant
        await db_session.execute(
            update(TenantModel).where(TenantModel.id == tenant.id).values(is_active=True)
        )
        await db_session.commit()
        # Force SQLAlchemy to re-fetch from DB on next query (clear identity map cache)
        db_session.expire_all()
        
        # Verify user can now access API
        response2 = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {jwt}"}
        )
        assert response2.status_code == 200
    
    @pytest.mark.asyncio
    async def test_reactivate_already_active_tenant_returns_400(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that reactivating already active tenant returns 400"""
        platform_admin_token = platform_admin_setup["token"]
        
        # Create active tenant
        tenant = await create_test_tenant(db_session, activation_status="active")
        assert tenant.is_active is True
        await db_session.commit()
        
        # Try to reactivate
        response = await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/reactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 400
        assert "already active" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_reactivate_nonexistent_tenant_returns_404(
        self,
        api_client: AsyncClient,
        platform_admin_setup
    ):
        """Test that reactivating non-existent tenant returns 404"""
        platform_admin_token = platform_admin_setup["token"]
        fake_tenant_id = uuid4()
        
        response = await api_client.patch(
            f"/api/platform/b2b/tenants/{fake_tenant_id}/reactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        assert response.status_code == 404


@pytest.mark.integration
class TestTenantDeactivationAudit:
    """Test audit logging for tenant deactivation/reactivation"""
    
    @pytest.mark.asyncio
    async def test_deactivation_is_logged_to_platform_audit(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that tenant deactivation creates audit log entry"""
        from modules.platform.models import PlatformAuditLog
        
        platform_admin_token = platform_admin_setup["token"]
        
        tenant = await create_test_tenant(db_session, activation_status="active")
        await db_session.commit()
        
        # Deactivate tenant
        await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/deactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        # Check audit log
        result = await db_session.execute(
            select(PlatformAuditLog)
            .where(PlatformAuditLog.action == "deactivate_tenant")
            .where(PlatformAuditLog.resource_id == str(tenant.id))
        )
        audit_entry = result.scalar_one_or_none()
        
        assert audit_entry is not None
        assert audit_entry.resource_type == "tenant"
    
    @pytest.mark.asyncio
    async def test_reactivation_is_logged_to_platform_audit(
        self,
        api_client: AsyncClient,
        platform_admin_setup,
        db_session: AsyncSession
    ):
        """Test that tenant reactivation creates audit log entry"""
        from modules.platform.models import PlatformAuditLog
        
        platform_admin_token = platform_admin_setup["token"]
        
        tenant = await create_test_tenant(db_session, activation_status="active")
        tenant.is_active = False
        await db_session.commit()
        
        # Reactivate tenant
        await api_client.patch(
            f"/api/platform/b2b/tenants/{tenant.id}/reactivate",
            headers={"Authorization": f"Bearer {platform_admin_token}"}
        )
        
        # Check audit log
        result = await db_session.execute(
            select(PlatformAuditLog)
            .where(PlatformAuditLog.action == "reactivate_tenant")
            .where(PlatformAuditLog.resource_id == str(tenant.id))
        )
        audit_entry = result.scalar_one_or_none()
        
        assert audit_entry is not None
        assert audit_entry.resource_type == "tenant"
