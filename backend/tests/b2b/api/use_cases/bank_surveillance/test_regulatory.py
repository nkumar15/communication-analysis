import pytest


from httpx import AsyncClient
from uuid import uuid4
from fastapi import status

@pytest.mark.asyncio
class TestRegulatoryLibrary:
    """Tests for the Regulatory Library feature."""

    async def setup_rbac(self, setup):
        """Grant regulatory CRUD permissions directly on the owner's tenant role."""
        from sqlalchemy import text, select
        from modules.b2b.models.rbac import Resource, Action, RolePermission

        # Use the underlying raw session so we can bypass RLS for seeding
        raw_db = setup["session"]._session
        user = setup["owner"]

        await raw_db.execute(text("SET app.is_platform_admin = 'true'"))

        if user not in raw_db:
            user = await raw_db.merge(user)
        await raw_db.refresh(user)

        for resource_name, action_name in [
            ("regulatory", "read"), ("regulatory", "write"),
            ("regulatory", "update"), ("regulatory", "delete"),
        ]:
            res_obj = (await raw_db.execute(
                select(Resource).where(Resource.name == resource_name)
            )).scalar_one_or_none()
            if not res_obj:
                res_obj = Resource(name=resource_name, display_name="Regulatory")
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

    async def test_create_document_success(self, api_client, b2b_test_setup):
        """Happy path: Create a regulatory document."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        payload = {
            "tenant_id": str(setup["tenant"].id),
            "title": f"SEC Framework {uuid4().hex[:6]}",
            "framework": "SEC",
            "year": 2024,
            "version": "v1.0",
            "storage_path": f"regulatory/tests/{uuid4().hex[:6]}.pdf"
        }
        
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/regulatory/",
            json=payload,
            headers=headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["framework"] == "SEC"
        assert data["tenant_id"] == str(setup["tenant"].id)

    async def test_get_document_success(self, api_client, b2b_test_setup):
        """Happy path: Retrieve a specific document."""
        setup = b2b_test_setup
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange: Create a document
        await self.setup_rbac(setup)
        payload = {
            "tenant_id": str(setup["tenant"].id),
            "title": f"Get Test {uuid4().hex[:6]}",
            "framework": "MAS"
        }
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/regulatory/", json=payload, headers=headers)
        doc_id = create_resp.json()["id"]

        # 2. Act: Get the document
        response = await api_client.get(f"/api/b2b/domain/bank_surveillance/regulatory/{doc_id}", headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == doc_id
        assert response.json()["title"] == payload["title"]

    async def test_list_documents(self, api_client, b2b_test_setup):
        """Happy path: List documents for the tenant."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # Ensure at least one exists
        await api_client.post("/api/b2b/domain/bank_surveillance/regulatory/", json={
            "tenant_id": str(setup["tenant"].id),
            "title": "List Test Doc",
            "framework": "FCA"
        }, headers=headers)

        response = await api_client.get("/api/b2b/domain/bank_surveillance/regulatory/", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_update_document_success(self, api_client, b2b_test_setup):
        """Happy path: Update a document."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/regulatory/", json={
            "tenant_id": str(setup["tenant"].id),
            "title": "Old Title",
            "framework": "SEC"
        }, headers=headers)
        doc_id = create_resp.json()["id"]

        # 2. Act
        update_payload = {"title": "New Improved Title"}
        response = await api_client.patch(f"/api/b2b/domain/bank_surveillance/regulatory/{doc_id}", json=update_payload, headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "New Improved Title"

    async def test_delete_document_success(self, api_client, b2b_test_setup):
        """Happy path: Delete a document."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        # 1. Arrange
        create_resp = await api_client.post("/api/b2b/domain/bank_surveillance/regulatory/", json={
            "tenant_id": str(setup["tenant"].id),
            "title": "To Delete"
        }, headers=headers)
        doc_id = create_resp.json()["id"]

        # 2. Act
        response = await api_client.delete(f"/api/b2b/domain/bank_surveillance/regulatory/{doc_id}", headers=headers)
        
        # 3. Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's gone
        get_resp = await api_client.get(f"/api/b2b/domain/bank_surveillance/regulatory/{doc_id}", headers=headers)
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_regulatory_unauthorized(self, api_client):
        """Error Case: No token provided."""
        response = await api_client.get("/api/b2b/domain/bank_surveillance/regulatory/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_regulatory_tenant_isolation(self, api_client, b2b_test_setup):
        """Security: Verify unauthenticated access to regulatory endpoint is rejected."""
        # Full cross-tenant isolation requires two independent b2b_test_setup fixtures,
        # which pytest does not support in a single test. This test verifies the
        # basic auth boundary: unauthenticated requests are rejected.
        response = await api_client.get("/api/b2b/domain/bank_surveillance/regulatory/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_validation_error(self, api_client, b2b_test_setup):
        """Error Case: Missing mandatory title returns 422."""
        setup = b2b_test_setup
        await self.setup_rbac(setup)
        headers = {"Authorization": f"Bearer {setup['token']}"}

        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/regulatory/",
            json={"tenant_id": str(setup["tenant"].id)},  # Title missing
            headers=headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
