"""
Integration tests for role management API
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from services.b2b.models import Role, RolePermission
from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)

@pytest_asyncio.fixture
async def role_test_data(db_session):
    """Setup tenant and admin user"""
    tenant = await create_test_tenant(db_session)
    admin = await create_test_user(
        db_session, 
        tenant_id=tenant.id, 
        email=f"admin@{tenant.domain}",
        role_slug="admin"
    )
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=admin.firebase_uid,
        email=admin.email
    ))
    return {
        "tenant": tenant,
        "admin": admin,
        "token": token
    }

@pytest.mark.integration
class TestRoleManagement:
    """Test role management endpoints"""

    @pytest.mark.asyncio
    async def test_list_templates(self, api_client: AsyncClient, role_test_data):
        """Test listing role templates"""
        token = role_test_data["token"]
        
        response = await api_client.get(
            "/api/b2b/roles/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check for standard templates
        names = [t["name"] for t in data]
        assert "admin" in names
        assert "viewer" in names

    @pytest.mark.asyncio
    async def test_create_role_no_template(self, api_client: AsyncClient, role_test_data, db_session):
        """Test creating a role without a template"""
        token = role_test_data["token"]
        tenant_id = role_test_data["tenant"].id
        
        role_name = f"custom_role_{uuid4().hex[:8]}"
        payload = {
            "name": role_name,
            "display_name": "Custom Role",
            "description": "A custom role"
        }
        
        response = await api_client.post(
            "/api/b2b/roles",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == role_name
        assert data["display_name"] == "Custom Role"
        assert data["is_system_role"] is False
        
        # Verify in DB
        result = await db_session.execute(
            select(Role).where(Role.id == data["id"])
        )
        role = result.scalar_one()
        assert role.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_create_role_with_template(self, api_client: AsyncClient, role_test_data, db_session):
        """Test creating a role from a template"""
        token = role_test_data["token"]
        
        # Get admin template
        response = await api_client.get(
            "/api/b2b/roles/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        templates = response.json()
        admin_template = next(t for t in templates if t["name"] == "admin")
        
        role_name = f"admin_clone_{uuid4().hex[:8]}"
        payload = {
            "name": role_name,
            "display_name": "Admin Clone",
            "template_id": admin_template["id"]
        }
        
        response = await api_client.post(
            "/api/b2b/roles",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        role_id = data["id"]
        
        # Verify permissions were copied
        result = await db_session.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
        permissions = result.scalars().all()
        assert len(permissions) > 0

    @pytest.mark.asyncio
    async def test_create_role_with_custom_permissions(self, api_client: AsyncClient, role_test_data, db_session):
        token = role_test_data["token"]
        
        # Get resources and actions first
        resources_response = await api_client.get("/api/b2b/roles/resources/all", headers={"Authorization": f"Bearer {token}"})
        assert resources_response.status_code == 200
        resources = resources_response.json()
        
        actions_response = await api_client.get("/api/b2b/roles/actions/all", headers={"Authorization": f"Bearer {token}"})
        assert actions_response.status_code == 200
        actions = actions_response.json()
        
        # Pick one resource and one action
        resource_id = resources[0]['id']
        action_id = actions[0]['id']
        
        payload = {
            "name": "custom_role",
            "display_name": "Custom Role",
            "description": "Role with custom permissions",
            "permissions": [
                {"resource_id": resource_id, "action_id": action_id}
            ]
        }
        
        response = await api_client.post("/api/b2b/roles", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "custom_role"
        
        # Verify permissions
        detail_response = await api_client.get(f"/api/b2b/roles/{data['id']}", headers={"Authorization": f"Bearer {token}"})
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail['permissions']) == 1
        assert detail['permissions'][0]['resource']['id'] == resource_id
        assert detail['permissions'][0]['action']['id'] == action_id

    @pytest.mark.asyncio
    async def test_delete_role(self, api_client: AsyncClient, role_test_data, db_session):
        """Test deleting a role"""
        token = role_test_data["token"]
        
        # Create a role first
        role_name = f"to_delete_{uuid4().hex[:8]}"
        payload = {
            "name": role_name,
            "display_name": "To Delete"
        }
        response = await api_client.post(
            "/api/b2b/roles",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        role_id = response.json()["id"]
        
        # Delete it
        response = await api_client.delete(
            f"/api/b2b/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify gone
        result = await db_session.execute(
            select(Role).where(Role.id == role_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_system_role_fails(self, api_client: AsyncClient, role_test_data, db_session):
        """Test that system roles cannot be deleted"""
        token = role_test_data["token"]
        tenant_id = role_test_data["tenant"].id
        
        # Find a system role (e.g. admin)
        result = await db_session.execute(
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .where(Role.name == "admin")
        )
        admin_role = result.scalar_one()
        
        response = await api_client.delete(
            f"/api/b2b/roles/{admin_role.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "system role" in response.json()["detail"]
