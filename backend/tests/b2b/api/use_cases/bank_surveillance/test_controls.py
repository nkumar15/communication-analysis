import pytest


from httpx import AsyncClient
from uuid import uuid4
from fastapi import status

@pytest.mark.asyncio
class TestSurveillanceControls:
    """Tests for the Surveillance Controls feature."""

    async def setup_rbac(self, setup):
        """Assign surveillance_chief role to the test user."""
        db = setup["session"]
        tenant_id = setup["tenant"].id
        user_id = setup["owner"].id

        from sqlalchemy import select
        from modules.b2b.models import Team, TeamMember
        from modules.b2b.models.team_role_definition import TeamRoleDefinition

        # 1. Get/Create Surveillance Team
        team_stmt = select(Team).where(Team.name == "Surveillance Team").where(Team.tenant_id == tenant_id)
        team = (await db.execute(team_stmt)).scalar_one_or_none()
        if not team:
            team = Team(tenant_id=tenant_id, name="Surveillance Team")
            db.add(team)
            await db.flush()

        # 2. Get surveillance_chief role
        from sqlalchemy import or_
        role_stmt = select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == "surveillance_chief",
            or_(TeamRoleDefinition.tenant_id.is_(None), TeamRoleDefinition.tenant_id == tenant_id)
        )
        role = (await db.execute(role_stmt)).scalar_one_or_none()
        
        if not role:
            # Fallback to searching without tenant_id if still not found
            role_stmt = select(TeamRoleDefinition).where(TeamRoleDefinition.name == "surveillance_chief")
            role = (await db.execute(role_stmt)).scalars().first()

        # 3. Assign role to user
        tm_stmt = select(TeamMember).where(TeamMember.user_id == user_id).where(TeamMember.team_id == team.id)
        tm = (await db.execute(tm_stmt)).scalar_one_or_none()
        if not tm:
            tm = TeamMember(
                team_id=team.id,
                user_id=user_id,
                team_role="surveillance_chief",
                team_role_id=role.id if role else None
            )
            db.add(tm)
            await db.flush()

    async def test_create_control_linked_success(self, api_client, b2b_test_setup):
        """Happy path: Create a control linked to a regulatory document."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange: Create a regulatory document
        reg_payload = {
            "tenant_id": str(setup["tenant"].id),
            "title": f"Reg For Control {uuid4().hex[:6]}",
            "framework": "MAS"
        }
        reg_resp = await api_client.post("/api/b2b/domain/bank_surveillance/regulatory/", json=reg_payload, headers=headers)
        reg_id = reg_resp.json()["id"]

        # 2. Act: Create control linked to it
        payload = {
            "tenant_id": str(setup["tenant"].id),
            "risk_typology": "Market Manipulation",
            "risk_indicator": f"Wash Trading {uuid4().hex[:6]}",
            "regulatory_id": reg_id,
            "regulatory_reference_text": "Section 1.2 of MAS Guide",
            "detection_methods": ["Keyword", "Threshold"],
            "status": "Active"
        }
        
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/controls/",
            json=payload,
            headers=headers
        )
        
        # 3. Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["risk_indicator"] == payload["risk_indicator"]
        assert data["regulatory_id"] == reg_id
        # Verify nested object mapping
        assert data["regulatory_document"]["id"] == reg_id
        assert data["regulatory_document"]["title"] == reg_payload["title"]

    async def test_get_control_details(self, api_client, b2b_test_setup):
        """Happy path: Retrieve control details with nested regulatory info."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/controls/", json={
            "tenant_id": str(setup["tenant"].id),
            "risk_typology": "Insider Trading",
            "risk_indicator": "Unusual Volume",
            "detection_methods": ["Semantic"]
        }, headers=headers)
        control_id = create_resp.json()["id"]

        # 2. Act
        response = await api_client.get(f"/api/b2b/domain/bank_surveillance/controls/{control_id}", headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == control_id
        assert "detection_methods" in response.json()

    async def test_list_controls_filtering(self, api_client, b2b_test_setup):
        """Happy path: List controls with typology filter."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        typology = f"Typology_{uuid4().hex[:6]}"
        await api_client.post("/api/b2b/domain/bank_surveillance/controls/", json={
            "tenant_id": str(setup["tenant"].id),
            "risk_typology": typology,
            "risk_indicator": "Filter Test"
        }, headers=headers)

        # Filter by typology
        response = await api_client.get(f"/api/b2b/domain/bank_surveillance/controls/?risk_typology={typology}", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert all(c["risk_typology"] == typology for c in data)

    async def test_update_control_success(self, api_client, b2b_test_setup):
        """Happy path: Update control status and methods."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/controls/", json={
            "tenant_id": str(setup["tenant"].id),
            "risk_typology": "Conflict",
            "risk_indicator": "Initial Indicator",
            "status": "Active"
        }, headers=headers)
        control_id = create_resp.json()["id"]

        # 2. Act
        update_payload = {
            "status": "Inactive",
            "detection_methods": ["Manual", "AI"]
        }
        response = await api_client.patch(f"/api/b2b/domain/bank_surveillance/controls/{control_id}", json=update_payload, headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "Inactive"
        assert sorted(data["detection_methods"]) == sorted(["Manual", "AI"])

    async def test_delete_control_success(self, api_client, b2b_test_setup):
        """Happy path: Delete a control."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/controls/", json={
            "tenant_id": str(setup["tenant"].id),
            "risk_typology": "Fraud",
            "risk_indicator": "Delete Me"
        }, headers=headers)
        control_id = create_resp.json()["id"]

        # 2. Act
        response = await api_client.delete(f"/api/b2b/domain/bank_surveillance/controls/{control_id}", headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify 404
        get_resp = await api_client.get(f"/api/b2b/domain/bank_surveillance/controls/{control_id}", headers=headers)
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_controls_unauthorized(self, api_client):
        """Error Case: Unauthorized access."""
        response = await api_client.get("/api/b2b/domain/bank_surveillance/controls/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
