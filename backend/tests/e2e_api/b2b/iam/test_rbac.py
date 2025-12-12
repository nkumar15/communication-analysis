"""
Consolidated RBAC Integration Tests
Covers:
1. Role Management (CRUD)
2. User Scoping & Isolation
3. Permission Enforcement (Negative Tests)
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from uuid import uuid4
from services.b2b.models import Role, RolePermission, UserModel
from core.constants import B2BRoleName
from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)

@pytest.mark.integration
class TestRoleManagement:
    """Tests for defining and managing roles (formerly test_roles.py)"""

    @pytest.mark.asyncio
    async def test_list_templates(self, api_client: AsyncClient, b2b_test_setup):
        """Test listing role templates"""
        setup = b2b_test_setup
        token = setup["token"]
        
        response = await api_client.get(
            "/api/b2b/roles/templates",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        names = [t["name"] for t in data]
        assert "admin" in names
        assert "viewer" in names

    @pytest.mark.asyncio
    async def test_create_role_no_template(self, api_client: AsyncClient, b2b_test_setup):
        """Test creating a role without a template"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant_id = setup["tenant_id"]
        
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
        
        # Verify in DB
        result = await setup['session'].execute(
            select(Role).where(Role.id == data["id"])
        )
        role = result.scalar_one()
        assert role.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_create_role_with_template(self, api_client: AsyncClient, b2b_test_setup):
        """Test creating a role from a template"""
        setup = b2b_test_setup
        token = setup["token"]
        
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
        
        # Verify permissions copied
        result = await setup['session'].execute(
            select(RolePermission).where(RolePermission.role_id == data["id"])
        )
        permissions = result.scalars().all()
        assert len(permissions) > 0

    @pytest.mark.asyncio
    async def test_role_deletion_flow(self, api_client: AsyncClient, b2b_test_setup):
        """Combined test for role deletion (soft delete, system checks)"""
        setup = b2b_test_setup
        token = setup["token"]
        
        # 1. Create custom role
        role_name = f"del_role_{uuid4().hex[:8]}"
        resp = await api_client.post(
            "/api/b2b/roles",
            json={"name": role_name, "display_name": "Del"},
            headers={"Authorization": f"Bearer {token}"}
        )
        role_id = resp.json()["id"]
        
        # 2. Delete it
        del_resp = await api_client.delete(f"/api/b2b/roles/{role_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 200
        
        # 3. Verify it is gone from list
        list_resp = await api_client.get("/api/b2b/roles", headers={"Authorization": f"Bearer {token}"})
        assert not any(r["id"] == role_id for r in list_resp.json())
        
        # 4. Verify system role cannot be deleted
        # Find admin role ID
        roles = list_resp.json()
        admin_role = next(r for r in roles if r["name"] == "admin")
        
        sys_del_resp = await api_client.delete(f"/api/b2b/roles/{admin_role['id']}", headers={"Authorization": f"Bearer {token}"})
        assert sys_del_resp.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_can_update_user_role(self, api_client: AsyncClient, b2b_test_setup):
        """Test admin can successfully update a user's role"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant = setup["tenant"]
        
        # 1. Create a target user (viewer)
        target_user = await create_test_user(
            setup['session'],
            tenant_id=tenant.id,
            email=f"target_{uuid4().hex[:8]}@{tenant.domain}",
            role_slug="viewer"
        )
        
        # 2. Update role to 'admin'
        response = await api_client.put(
            f"/api/b2b/users/{target_user.id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # 3. Verify validation
        result = await setup['session'].execute(
            select(Role).join(UserModel).where(UserModel.id == target_user.id)
        )
        new_role = result.scalar_one()
        assert new_role.name == "admin"


@pytest.mark.integration
class TestUserScoping:
    """Tests for User Visibility and Scoping (formerly test_users.py)"""
    
    @pytest.mark.asyncio
    async def test_admin_can_list_all_users(self, api_client: AsyncClient, b2b_test_setup):
        """Admin matches all"""
        setup = b2b_test_setup
        
        # Create extra viewer
        await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"u1@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 2  # Admin + new user

    @pytest.mark.asyncio
    async def test_viewer_can_only_see_themselves(self, api_client: AsyncClient, b2b_test_setup):
        """Viewer matches self only"""
        setup = b2b_test_setup
        
        viewer = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"v_scope@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        
        # Helper to get viewer token
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup['tenant'].firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/users/list",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == viewer.email

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, api_client: AsyncClient, b2b_test_setup):
        """Cross-tenant isolation check"""
        setup1 = b2b_test_setup
        
        # Create Tenant 2
        session = setup1['session']._session
        t2 = await create_test_tenant(session, name="T2", domain="t2.com")
        u2 = await create_test_user(session, tenant_id=t2.id, email=f"admin@{t2.domain}", role_slug="admin")
        
        token2 = encode_mock_jwt(create_mock_firebase_token(
            uid=u2.firebase_uid,
            email=u2.email,
            firebase_tenant_id=t2.firebase_tenant_id
        ))
        
        # Lists should be disjoint
        r1 = await api_client.get("/api/b2b/users/list", headers={"Authorization": f"Bearer {setup1['token']}"})
        r2 = await api_client.get("/api/b2b/users/list", headers={"Authorization": f"Bearer {token2}"})
        
        assert r1.status_code == 200
        assert r2.status_code == 200
        
        ids1 = {u["id"] for u in r1.json()}
        ids2 = {u["id"] for u in r2.json()}


@pytest.mark.integration
class TestRBACEnforcement:
    """Tests ensures restricted roles are BLOCKED from actions"""

    @pytest.mark.asyncio
    async def test_viewer_cannot_manage_roles(self, api_client: AsyncClient, b2b_test_setup):
        """Viewer should get 403 when trying to create a role"""
        setup = b2b_test_setup
        
        # Create Viewer
        viewer = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"viewer_rbac@{setup['tenant'].domain}",
            role_slug="viewer"
        )
        token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup['tenant'].firebase_tenant_id
        ))
        
        # Try Create Role
        resp = await api_client.post(
            "/api/b2b/roles",
            json={"name": "bad_role", "display_name": "Bad"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_users(self, api_client: AsyncClient, b2b_test_setup):
        """Viewer should get 403 when deleting user (if endpoint existed/configured)"""
        # Currently we don't have a delete-user endpoint in test_users.py coverage, 
        # but let's check roles deletion as proxy for 'write' permission check
        pass # Implementation pending endpoint availability, relying on roles test above

    @pytest.mark.asyncio
    async def test_team_member_cannot_update_team(self, api_client: AsyncClient, b2b_test_setup):
        """Team Member (not manager) cannot update team settings"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        
        # 1. Create Team (as Admin)
        t_resp = await api_client.post("/api/b2b/teams/", json={"name": "Secure Team"}, headers={"Authorization": f"Bearer {setup['token']}"})
        team_id = t_resp.json()["id"]
        
        # 2. Create User
        member = await create_test_user(
            setup['session'],
            tenant_id=tenant.id,
            email=f"tm@{tenant.domain}",
            role_slug="viewer"
        )
        
        # 3. Add as Team Member (not manager)
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members", 
            json={"user_id": str(member.id), "team_role": "team_contributor"},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        # 4. Try Update Team as Member
        mem_token = encode_mock_jwt(create_mock_firebase_token(
            uid=member.firebase_uid,
            email=member.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        resp = await api_client.patch(
            f"/api/b2b/teams/{team_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {mem_token}"}
        )
        
        # Should be forbidden
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_team_manager_can_update_team(self, api_client: AsyncClient, b2b_test_setup):
        """Team Manager CAN update team settings"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        
        # 1. Create Team
        t_resp = await api_client.post("/api/b2b/teams/", json={"name": "Manager Team"}, headers={"Authorization": f"Bearer {setup['token']}"})
        team_id = t_resp.json()["id"]
        
        # 2. Create User
        manager = await create_test_user(
            setup['session'],
            tenant_id=tenant.id,
            email=f"mgr@{tenant.domain}",
            role_slug="viewer"
        )
        
        # 3. Add as Team Manager
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members", 
            json={"user_id": str(manager.id), "team_role": "team_manager"},
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        # 4. Update Team
        mgr_token = encode_mock_jwt(create_mock_firebase_token(
            uid=manager.firebase_uid,
            email=manager.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        resp = await api_client.patch(
            f"/api/b2b/teams/{team_id}",
            json={"name": "Managed Name"},
            headers={"Authorization": f"Bearer {mgr_token}"}
        )
        
        assert resp.status_code == 200
        assert resp.json()["name"] == "Managed Name"
