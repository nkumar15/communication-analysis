"""
E2E API Tests for Platform Roles Management

Tests the /api/platform/roles endpoints including:
- Listing roles with permissions
- Creating new roles
- Permission enforcement
- Response schema validation
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from tests.conftest import (
    create_mock_firebase_token,
    encode_mock_jwt,
    create_platform_tenant,
    create_platform_user
)


@pytest.mark.integration
class TestPlatformRoles:
    """Test platform roles API endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_roles_requires_authentication(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that listing roles requires authentication"""
        response = await api_client.get("/api/platform/roles/")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_list_roles_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test listing roles with proper authentication"""
        unique_email = f"admin-{uuid4().hex[:8]}@platform.net"
        
        # Setup platform admin
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
        
        response = await api_client.get(
            "/api/platform/roles/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        roles = response.json()
        
        # Should return list of roles
        assert isinstance(roles, list)
        assert len(roles) >= 3  # At least platform_admin, support_staff, billing_manager
        
        # Verify role structure
        for role in roles:
            assert "id" in role
            assert "name" in role
            assert "display_name" in role
            assert "is_system_role" in role
            assert "permissions" in role
            assert isinstance(role["permissions"], list)
            
            # Verify permission structure
            for perm in role["permissions"]:
                assert "resource" in perm
                assert "action" in perm
    
    @pytest.mark.asyncio
    async def test_system_roles_have_correct_permissions(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Verify that seeded system roles have expected permissions"""
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
        
        response = await api_client.get(
            "/api/platform/roles/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        roles = response.json()
        
        # Find platform_admin role
        platform_admin_role = next((r for r in roles if r["name"] == "platform_admin"), None)
        assert platform_admin_role is not None
        assert platform_admin_role["is_system_role"] is True
        
        # platform_admin should have *:* permission
        permissions = platform_admin_role["permissions"]
        has_wildcard = any(
            p["resource"] == "*" and p["action"] == "*"
            for p in permissions
        )
        assert has_wildcard, "platform_admin should have *:* permission"
        
        # Find support_staff role
        support_staff = next((r for r in roles if r["name"] == "support_staff"), None)
        assert support_staff is not None
        assert support_staff["is_system_role"] is True
        
        # support_staff should have specific permissions (not full wildcard)
        support_permissions = support_staff["permissions"]
        assert len(support_permissions) > 0
        
        # Find billing_manager role
        billing_manager = next((r for r in roles if r["name"] == "billing_manager"), None)
        assert billing_manager is not None
        assert billing_manager["is_system_role"] is True
    
    @pytest.mark.asyncio
    async def test_create_role_requires_authentication(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that creating roles requires authentication"""
        response = await api_client.post(
            "/api/platform/roles/",
            json={
                "name": "test_role",
                "display_name": "Test Role",
                "description": "Test"
            }
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_create_role_success(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test creating a new role with proper permissions"""
        unique_email = f"creator-{uuid4().hex[:8]}@platform.net"
        
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
        
        role_data = {
            "name": f"custom_analyst_{uuid4().hex[:6]}",
            "display_name": "Data Analyst",
            "description": "Read-only access to analytics data"
        }
        
        response = await api_client.post(
            "/api/platform/roles/",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json=role_data
        )
        
        assert response.status_code == 200
        created_role = response.json()
        
        # Verify response structure
        assert created_role["name"] == role_data["name"]
        assert created_role["display_name"] == role_data["display_name"]
        assert created_role["description"] == role_data["description"]
        assert created_role["is_system_role"] is False  # Custom roles are not system roles
        assert "id" in created_role
        assert "created_at" in created_role
        
        # Verify role appears in list
        list_response = await api_client.get(
            "/api/platform/roles/",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert list_response.status_code == 200
        roles = list_response.json()
        role_names = [r["name"] for r in roles]
        assert role_data["name"] in role_names
