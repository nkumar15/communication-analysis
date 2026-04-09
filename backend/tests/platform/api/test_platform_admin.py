"""
Integration tests for platform admin functionality
Tests authentication, tenant management, and stats
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from modules.platform.models import PlatformUser, PlatformRole
from core.constants import PlatformRoleName, B2BRoleName
from modules.b2b.models import TenantModel
from modules.b2b.models.rbac import Role
from core.config import settings

from tests.conftest import (
    create_mock_firebase_token,
    encode_mock_jwt,
    create_platform_tenant,
    create_platform_user,
    create_test_tenant,
    create_test_user
)


@pytest.mark.integration
class TestPlatformAdmin:
    """Test platform admin API endpoints"""
    
    @pytest.mark.asyncio
    async def test_platform_admin_auth_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Platform admin can authenticate and get info"""
        from uuid import uuid4
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        # Setup platform tenant and admin
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            
            email=unique_email,
            role_name="platform_admin"
        )
        
        # Mock JWT
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/platform/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin.email
        assert data["role"] == "platform_admin"
        assert data["tenant_id"] == str(platform_tenant.id)

    @pytest.mark.asyncio
    async def test_platform_stats(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Platform admin can view global stats"""
        from uuid import uuid4
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        # Setup platform tenant and admin
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            
            email=unique_email,
            role_name="platform_admin"
        )
        
        # Create some regular tenants
        await create_test_tenant(db_session, name="Tenant 1", activation_status="active")
        await create_test_tenant(db_session, name="Tenant 2", activation_status="pending")
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/platform/b2b/stats",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Total tenants = 2 regular (Platform tenant is NOT in tenants table)
        assert data["total_tenants"] >= 2 
        assert data["active_tenants"] >= 1 # Tenant 1

    @pytest.mark.asyncio
    async def test_create_tenant(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Platform admin can create new tenants"""
        from uuid import uuid4
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        platform_tenant = await create_platform_tenant(db_session)
        admin = await create_platform_user(
            db_session,
            
            email=unique_email,
            role_name="platform_admin"
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=admin.firebase_uid,
            email=admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        # Use randomized domain to prevent conflicts from committed data
        from uuid import uuid4
        domain_suffix = uuid4().hex[:8]
        test_domain = f"enterprise-{domain_suffix}.com"
        
        payload = {
            "name": "New Enterprise",
            "domain": test_domain,
            "admin_email": f"admin@{test_domain}",
            "plan": "pro"
        }
        
        response = await api_client.post(
            "/api/platform/b2b/tenants",
            json=payload,
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["message"] == "Tenant created successfully"
        
        # Verify in DB
        # Verify tenant was created
        from modules.b2b.models import TenantModel
        result = await db_session.execute(
            select(TenantModel).where(TenantModel.domain == test_domain)
        )
        tenant = result.scalar_one_or_none()
        assert tenant is not None
        assert tenant.name == "New Enterprise"

    @pytest.mark.asyncio
    async def test_impersonate_tenant_admin(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Platform admin can impersonate tenant admin"""
        from uuid import uuid4
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        # Setup platform
        platform_tenant = await create_platform_tenant(db_session)
        platform_admin = await create_platform_user(
            db_session,
            
            email=unique_email,
            role_name=PlatformRoleName.PLATFORM_ADMIN
        )
        
        # Setup target tenant
        target_tenant = await create_test_tenant(db_session)
        target_admin = await create_test_user(
            db_session,
            tenant_id=target_tenant.id,
            email=f"admin@{target_tenant.domain}",
            role_slug=B2BRoleName.ADMIN
        )
        assert target_admin.role_id is not None, "Admin user created without role!"
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=platform_admin.firebase_uid,
            email=platform_admin.email,
            firebase_tenant_id=platform_tenant.firebase_tenant_id
        ))
        
        response = await api_client.post(
            f"/api/platform/b2b/tenants/{target_tenant.id}/impersonate",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["tenant_id"] == str(target_tenant.id)
        assert data["admin_email"] == target_admin.email
