import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from services.b2b.models import Team, TeamMember
from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)

@pytest.mark.integration
class TestTeamManagement:
    """Test team management endpoints"""

    @pytest.mark.asyncio
    async def test_list_teams(self, api_client: AsyncClient, b2b_test_setup):
        """Test listing all teams""" 
        setup = b2b_test_setup
        token = setup["token"]
        
        response = await api_client.get(
            "/api/b2b/teams/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the default team
        assert len(data) >= 1
        assert any(t["is_default"] for t in data)

    @pytest.mark.asyncio
    async def test_create_team(self, api_client: AsyncClient, b2b_test_setup):
        """Test creating a team"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant_id = setup["tenant_id"]
        
        team_name = f"Team {uuid4().hex[:8]}"
        payload = {
            "name": team_name,
            "description": "A test team"
        }
        
        response = await api_client.post(
            "/api/b2b/teams/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == team_name
        assert data["description"] == "A test team"
        
        # Verify in DB with automatic tenant context
        result = await setup['session'].execute(
            select(Team).where(Team.id == data["id"])
        )
        team = result.scalar_one()
        assert team.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_update_team(self, api_client: AsyncClient, b2b_test_setup):
        """Test updating a team"""
        setup = b2b_test_setup
        token = setup["token"]
        
        # Create team first
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "Original Name"},
            headers={"Authorization": f"Bearer {token}"}
        )
        # Debug: Check if create succeeded
        assert create_response.status_code == 201, f"Create failed with {create_response.status_code}: {create_response.text}"
        team_id = create_response.json()["id"]
        
        # Update
        response = await api_client.patch(
            f"/api/b2b/teams/{team_id}",
            json={"name": "Updated Name", "description": "Updated Desc"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Update failed with {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Desc"

    @pytest.mark.asyncio
    async def test_delete_team(self, api_client: AsyncClient, b2b_test_setup):
        """Test deleting a team"""
        setup = b2b_test_setup
        token = setup["token"]
        
        # Create team
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "To Delete"},
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = create_response.json()["id"]
        
        # Delete
        response = await api_client.delete(
            f"/api/b2b/teams/{team_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify soft deleted with automatic context
        result = await setup['session'].execute(
            select(Team).where(Team.id == team_id)
        )
        team = result.scalar_one()
        assert team.deleted_at is not None

    @pytest.mark.asyncio
    async def test_add_team_member(self, api_client: AsyncClient, b2b_test_setup):
        """Test adding a member to a team"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant_id = setup["tenant_id"]
        tenant = setup["tenant"]
        
        # Create team
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "Member Test Team"},
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = create_response.json()["id"]
        
        # Create another user with tenant-aware session
        user = await create_test_user(
            setup['session'],
            tenant_id=tenant_id,
            email=f"member@{tenant.domain}",
            role_slug="viewer"
        )
        
        # Add member
        response = await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_member"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert data["team_role"] == "team_member"

    @pytest.mark.asyncio
    async def test_list_team_members(self, api_client: AsyncClient, b2b_test_setup):
        """Test listing team members"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant = setup["tenant"]
        
        # Create team
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "List Members Team"},
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = create_response.json()["id"]
        
        # Add a member
        user = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"list_member@{tenant.domain}",
            role_slug="viewer"
        )
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_manager"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # List members
        response = await api_client.get(
            f"/api/b2b/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == str(user.id)
        assert data[0]["team_role"] == "team_manager"

    @pytest.mark.asyncio
    async def test_update_team_member_role(self, api_client: AsyncClient, b2b_test_setup):
        """Test updating a team member's role"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant = setup["tenant"]
        
        # Create team & add member
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "Update Role Team"},
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = create_response.json()["id"]
        
        user = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"update_role@{tenant.domain}",
            role_slug="viewer"
        )
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_member"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Update role
        response = await api_client.patch(
            f"/api/b2b/teams/{team_id}/members/{user.id}",
            json={"team_role": "team_manager"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_role"] == "team_manager"

    @pytest.mark.asyncio
    async def test_remove_team_member(self, api_client: AsyncClient, b2b_test_setup):
        """Test removing a team member"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant = setup["tenant"]
        
        # Create team & add member
        create_response = await api_client.post(
            "/api/b2b/teams/",
            json={"name": "Remove Member Team"},
            headers={"Authorization": f"Bearer {token}"}
        )
        team_id = create_response.json()["id"]
        
        user = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"remove_member@{tenant.domain}",
            role_slug="viewer"
        )
        await api_client.post(
            f"/api/b2b/teams/{team_id}/members",
            json={"user_id": str(user.id), "team_role": "team_member"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Remove member
        response = await api_client.delete(
            f"/api/b2b/teams/{team_id}/members/{user.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify removed
        response = await api_client.get(
            f"/api/b2b/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_move_team_member(self, api_client: AsyncClient, b2b_test_setup):
        """Test moving a user between teams"""
        setup = b2b_test_setup
        token = setup["token"]
        tenant = setup["tenant"]
        
        # Create two teams
        t1_resp = await api_client.post("/api/b2b/teams/", json={"name": "Team 1"}, headers={"Authorization": f"Bearer {token}"})
        t1_id = t1_resp.json()["id"]
        
        t2_resp = await api_client.post("/api/b2b/teams/", json={"name": "Team 2"}, headers={"Authorization": f"Bearer {token}"})
        t2_id = t2_resp.json()["id"]
        
        # Create user and add to Team 1
        user = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"move_member@{tenant.domain}",
            role_slug="viewer"
        )
        await api_client.post(
            f"/api/b2b/teams/{t1_id}/members",
            json={"user_id": str(user.id), "team_role": "team_member"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Move to Team 2
        response = await api_client.post(
            f"/api/b2b/teams/members/{user.id}/move",
            json={"from_team_id": t1_id, "to_team_id": t2_id, "team_role": "team_manager"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Verify removed from Team 1
        r1 = await api_client.get(f"/api/b2b/teams/{t1_id}/members", headers={"Authorization": f"Bearer {token}"})
        assert len(r1.json()) == 0
        
        # Verify added to Team 2
        r2 = await api_client.get(f"/api/b2b/teams/{t2_id}/members", headers={"Authorization": f"Bearer {token}"})
        assert len(r2.json()) == 1
        assert r2.json()[0]["user_id"] == str(user.id)
        assert r2.json()[0]["team_role"] == "team_manager"
