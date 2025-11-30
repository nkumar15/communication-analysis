import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.b2b.models import TenantModel
from core.database import get_db
from uuid import uuid4

@pytest.mark.asyncio
class TestSoftDelete:
    async def test_soft_delete_tenant_flow(
        self,
        api_client: AsyncClient,
        platform_admin_setup: dict,
        db_session: AsyncSession
    ):
        # Construct headers from setup fixture
        platform_auth_headers = {
            "Authorization": f"Bearer {platform_admin_setup['token']}"
        }
        """
        Test complete soft delete flow:
        1. Create tenant
        2. Verify existence
        3. Delete tenant
        4. Verify removal from list
        5. Verify persistence in DB (soft deleted)
        """
        # 1. Create Tenant
        suffix = uuid4().hex[:8]
        tenant_data = {
            "name": f"Soft Delete Test {suffix}",
            "domain": f"soft-delete-{suffix}.com",
            "admin_email": f"admin-{suffix}@soft-delete.com"
        }
        
        response = await api_client.post(
            "/api/platform/tenants",
            json=tenant_data,
            headers=platform_auth_headers
        )
        assert response.status_code == 200
        tenant_id = response.json()["id"]
        
        # 2. Verify existence in list
        response = await api_client.get(
            "/api/platform/tenants",
            headers=platform_auth_headers
        )
        assert response.status_code == 200
        tenants = response.json()
        assert any(t["id"] == tenant_id for t in tenants)
        
        # 3. Delete Tenant
        response = await api_client.delete(
            f"/api/platform/tenants/{tenant_id}",
            headers=platform_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Tenant deleted successfully"
        
        # 4. Verify removal from list
        response = await api_client.get(
            "/api/platform/tenants",
            headers=platform_auth_headers
        )
        assert response.status_code == 200
        tenants = response.json()
        assert not any(t["id"] == tenant_id for t in tenants)
        
        # 5. Verify persistence in DB (Direct DB check)
        # We need to use a new session or ensure the current one sees the changes
        # Since the API runs in a separate transaction context, we might need to commit/refresh
        
        # Query directly for the tenant, ignoring soft delete filter if possible
        # But our service filters it. We should query the model directly.
        
        stmt = select(TenantModel).where(TenantModel.id == tenant_id)
        result = await db_session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        assert tenant is not None
        assert tenant.deleted_at is not None
        assert tenant.is_active == False
