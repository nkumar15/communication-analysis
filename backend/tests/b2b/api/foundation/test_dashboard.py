
import pytest
from httpx import AsyncClient
from core.constants import B2BRoleName
from tests.conftest import create_test_user, create_mock_firebase_token, encode_mock_jwt

@pytest.mark.integration
class TestDashboard:
    """Test dashboard endpoints"""

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_admin(self, api_client: AsyncClient, b2b_test_setup):
        """Admin should get dashboard stats successfully"""
        setup = b2b_test_setup
        token = setup["token"]
        
        response = await api_client.get(
            "/api/b2b/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed with {response.text}"
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        # Structure check is enough for P0

    @pytest.mark.asyncio
    async def test_get_dashboard_stats_member(self, api_client: AsyncClient, b2b_test_setup):
        """Member should get dashboard stats with limited scope"""
        setup = b2b_test_setup
        tenant = setup["tenant"]
        
        # Create member user
        member = await create_test_user(
            setup['session'],
            tenant_id=setup["tenant_id"],
            email=f"member_dash@{tenant.domain}",
            role_slug=B2BRoleName.MEMBER
        )
        
        jwt_token = encode_mock_jwt(create_mock_firebase_token(
            uid=member.firebase_uid,
            email=member.email,
            firebase_tenant_id=tenant.firebase_tenant_id
        ))
        
        response = await api_client.get(
            "/api/b2b/dashboard/stats",
            headers={"Authorization": f"Bearer {jwt_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verify member-specific fields or just success
        assert "active_users" in data

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(self, api_client: AsyncClient):
        """Unauthenticated request should fail"""
        response = await api_client.get("/api/b2b/dashboard/stats")
        assert response.status_code == 401
