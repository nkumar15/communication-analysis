import pytest


from httpx import AsyncClient
from uuid import uuid4
from fastapi import status

@pytest.mark.asyncio
class TestSurveillanceControls:
    """Tests for the Surveillance Controls feature."""

    async def setup_rbac(self, setup):
        """Grant controls and regulatory CRUD permissions directly on the owner's tenant role."""
        from sqlalchemy import text, select
        from modules.b2b.models.rbac import Resource, Action, RolePermission

        raw_db = setup["session"]._session
        user = setup["owner"]

        await raw_db.execute(text("SET app.is_platform_admin = 'true'"))

        if user not in raw_db:
            user = await raw_db.merge(user)
        await raw_db.refresh(user)

        for resource_name, action_name in [
            ("controls", "read"), ("controls", "write"),
            ("controls", "update"), ("controls", "delete"),
            # controls tests also create regulatory docs as fixtures
            ("regulatory", "read"), ("regulatory", "write"),
        ]:
            res_obj = (await raw_db.execute(
                select(Resource).where(Resource.name == resource_name)
            )).scalar_one_or_none()
            if not res_obj:
                res_obj = Resource(name=resource_name, display_name=resource_name.title())
                raw_db.add(res_obj)
                await raw_db.flush()

            act_obj = (await raw_db.execute(
                select(Action).where(Action.name == action_name)
            )).scalar_one_or_none()
            if not act_obj:
                act_obj = Action(name=action_name, display_name=action_name.title())
                raw_db.add(act_obj)
                await raw_db.flush()

            perm = (await raw_db.execute(select(RolePermission).where(
                RolePermission.role_id == user.role_id,
                RolePermission.resource_id == res_obj.id,
                RolePermission.action_id == act_obj.id,
            ))).scalar_one_or_none()
            if not perm:
                raw_db.add(RolePermission(
                    role_id=user.role_id,
                    resource_id=res_obj.id,
                    action_id=act_obj.id,
                ))
                await raw_db.flush()

        await raw_db.execute(text("SET app.is_platform_admin = 'false'"))
        await raw_db.commit()

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
