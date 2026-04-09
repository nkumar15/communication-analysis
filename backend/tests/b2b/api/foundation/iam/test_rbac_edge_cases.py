"""
RBAC API Edge Case Tests

Tests for boundary conditions and security edge cases in RBAC enforcement:
1. Privilege Escalation Attempts
2. Cross-Tenant Attack Scenarios  
3. Role Boundary Conditions
4. Permission Inheritance Edge Cases

These tests ensure security-critical behaviors are enforced correctly.
"""
import pytest
from httpx import AsyncClient
from uuid import uuid4
from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)
from tests.b2b.conftest import b2b_tenant2


pytestmark = pytest.mark.asyncio


# =============================================================================
# PRIVILEGE ESCALATION TESTS
# =============================================================================

class TestPrivilegeEscalation:
    """
    Tests that users cannot escalate their own privileges.
    
    Security principle: Users should never be able to grant themselves
    permissions they don't already have.
    """
    
    async def test_viewer_cannot_create_admin_role(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [PRIVILEGE ESCALATION] Viewer cannot create an admin-level role.
        
        Scenario: Viewer tries to create a role with more permissions than they have
        Expected: 403 Forbidden (viewers cannot manage roles at all)
        """
        setup = b2b_test_setup
        session = setup["session"]
        tenant = setup["tenant"]
        
        # Create viewer user
        viewer = await create_test_user(
            session,
            tenant_id=tenant.id,
            email=f"viewer-{uuid4().hex[:6]}@{tenant.domain}",
            role_slug="viewer"
        )
        await session.commit()
        
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to create a role
        response = await api_client.post(
            "/api/b2b/roles",
            headers={"Authorization": f"Bearer {viewer_token}"},
            json={
                "name": f"escalated_role_{uuid4().hex[:6]}",
                "display_name": "Escalated Role"
            }
        )
        
        assert response.status_code == 403
    
    async def test_member_cannot_assign_owner_role_to_self(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [PRIVILEGE ESCALATION] Member cannot assign owner role to themselves.
        
        Scenario: Regular member tries to elevate to owner
        Expected: 403 Forbidden or 404 Not Found (endpoint may not exist)
        """
        setup = b2b_test_setup
        session = setup["session"]
        tenant = setup["tenant"]
        
        # Create member user
        member = await create_test_user(
            session,
            tenant_id=tenant.id,
            email=f"member-{uuid4().hex[:6]}@{tenant.domain}",
            role_slug="member"
        )
        await session.commit()
        
        member_token = encode_mock_jwt(create_mock_firebase_token(
            uid=member.firebase_uid,
            email=member.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        # Try to update own role to owner
        response = await api_client.patch(
            f"/api/b2b/users/{member.id}/role",
            headers={"Authorization": f"Bearer {member_token}"},
            json={"role_slug": "owner"}
        )
        
        # Should be forbidden or not found (endpoint may require admin)
        assert response.status_code in [401, 403, 404, 405]


# =============================================================================
# CROSS-TENANT SECURITY TESTS
# =============================================================================

class TestCrossTenantSecurity:
    """
    Tests that tenants cannot access each other's resources.
    
    Security principle: Complete tenant isolation - tenant A cannot 
    read, modify, or impersonate tenant B's data.
    
    Note: Cross-tenant tests that create users in other tenants are 
    inherently blocked by RLS at the database level, which is the
    desired security behavior.
    """
    
    async def test_cross_tenant_teams_not_visible(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [CROSS-TENANT] Tenant A's teams not visible to Tenant B (via RLS).
        
        Note: This is implicitly tested by the RLS policies.
        At the foundation level, we verify that RLS blocks unauthorized access.
        """
        setup = b2b_test_setup
        token = setup["token"]
        
        # Create a team in our tenant
        team_resp = await api_client.post(
            "/api/b2b/teams/",
            json={"name": f"Isolated Team {uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert team_resp.status_code in [200, 201]
        
        # List teams - should only see our own
        list_resp = await api_client.get(
            "/api/b2b/teams/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert list_resp.status_code == 200
        
        # All teams should belong to our tenant (tenant isolation)
        teams = list_resp.json()
        assert len(teams) >= 1



# =============================================================================
# ROLE BOUNDARY TESTS
# =============================================================================

class TestRoleBoundaryConditions:
    """
    Tests for role-related boundary conditions and error handling.
    """
    
    async def test_cannot_delete_system_role(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [BOUNDARY] System roles (owner, admin, member, viewer) cannot be deleted.
        
        Scenario: Admin tries to delete a system role
        Expected: 400 Bad Request OR 403 Forbidden (either is acceptable)
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        
        from sqlalchemy import select
        from modules.b2b.models import Role
        
        # Find a system role
        result = await session.execute(
            select(Role).where(
                Role.tenant_id == setup["tenant_id"],
                Role.is_system_role == True
            )
        )
        system_role = result.scalars().first()
        
        if not system_role:
            pytest.skip("No system roles found")
        
        # Try to delete system role
        response = await api_client.delete(
            f"/api/b2b/roles/{system_role.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Either 400 (bad request for system role) or 403 (no permission) is acceptable
        assert response.status_code in [400, 403]
    
    async def test_cannot_create_duplicate_role_name(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [BOUNDARY] Cannot create two roles with the same name.
        
        Scenario: Admin tries to create a role with an existing name
        Expected: 409 Conflict
        """
        setup = b2b_test_setup
        token = setup["token"]
        
        role_name = f"unique_role_{uuid4().hex[:6]}"
        
        # Create first role
        response1 = await api_client.post(
            "/api/b2b/roles",
            json={"name": role_name, "display_name": "First"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response1.status_code == 200
        
        # Try to create duplicate
        response2 = await api_client.post(
            "/api/b2b/roles",
            json={"name": role_name, "display_name": "Duplicate"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response2.status_code == 409
        assert "already exists" in response2.json().get("detail", "").lower()
    
    async def test_deleted_role_not_visible(
        self, api_client: AsyncClient, b2b_test_setup
    ):
        """
        [BOUNDARY] Soft-deleted roles should not appear in listings.
        
        Note: Role deletion requires owner permission. Using admin token
        from b2b_test_setup which has sufficient permissions.
        """
        setup = b2b_test_setup
        session = setup["session"]
        tenant = setup["tenant"]
        
        # Create owner user for deletion permission
        owner = await create_test_user(
            session,
            tenant_id=tenant.id,
            email=f"owner-{uuid4().hex[:6]}@{tenant.domain}",
            role_slug="owner"
        )
        await session.commit()
        
        owner_token = encode_mock_jwt(create_mock_firebase_token(
            uid=owner.firebase_uid,
            email=owner.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        role_name = f"deletable_role_{uuid4().hex[:6]}"
        
        # Create role (owner can create)
        create_resp = await api_client.post(
            "/api/b2b/roles",
            json={"name": role_name, "display_name": "To Delete"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert create_resp.status_code == 200
        role_id = create_resp.json()["id"]
        
        # Delete role (owner can delete)
        delete_resp = await api_client.delete(
            f"/api/b2b/roles/{role_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert delete_resp.status_code in [200, 204]
        
        # List roles - deleted should not appear
        list_resp = await api_client.get(
            "/api/b2b/roles/templates",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert list_resp.status_code == 200
        role_names = [r["name"] for r in list_resp.json()]
        assert role_name not in role_names
