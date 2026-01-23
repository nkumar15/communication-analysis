
import pytest
from httpx import AsyncClient
from uuid import uuid4
from modules.b2b.models.geographic_region import GeographicRegion
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt

@pytest.mark.integration
class TestRegions:
    """Test regions endpoints"""

    @pytest.mark.asyncio
    async def test_list_regions(self, api_client: AsyncClient, b2b_test_setup):
        """Test listing regions for tenant"""
        setup = b2b_test_setup
        token = setup["token"]
        session = setup['session']
        tenant_id = setup['tenant_id']
        
        # Seed a region for this tenant
        region = GeographicRegion(
            tenant_id=tenant_id,
            code="US-TEST",
            name="Test Region"
        )
        session.add(region)
        await session.commit()
        
        response = await api_client.get(
            "/api/b2b/regions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(r["code"] == "US-TEST" for r in data)

    @pytest.mark.asyncio
    async def test_regions_isolation(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """Verify cross-tenant isolation for regions"""
        setup = b2b_test_setup
        
        # Create another tenant and region
        other_tenant = await create_test_tenant(db_session)
        other_region = GeographicRegion(
            tenant_id=other_tenant.id,
            code="EU-TEST",
            name="Europe Test"
        )
        db_session.add(other_region)
        await db_session.commit()
        
        # Query with first tenant's token
        response = await api_client.get(
            "/api/b2b/regions/",
            headers={"Authorization": f"Bearer {setup['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should NOT see other tenant's region
        assert not any(r["code"] == "EU-TEST" for r in data)
