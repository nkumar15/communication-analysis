"""
Security tests for multi-tenant isolation
Ensures data cannot leak across tenants
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    create_mock_firebase_token, 
    encode_mock_jwt,
    create_test_tenant,
    create_test_user,
    create_test_invitation
)


@pytest.mark.security
class TestMultiTenantIsolation:
    """Test multi-tenant data isolation"""
    
    @pytest.mark.asyncio
    async def test_cross_tenant_invitation_listing_blocked(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Tenant A admin cannot see Tenant B's invitations"""
        # Create two tenants
        tenant_a = await create_test_tenant(
            db_session,
            name="Company A"   
        )
        tenant_b = await create_test_tenant(
            db_session,
            name="Company B"
        )
        
        # Create admins for each
        admin_a = await create_test_user(
            db_session,
            tenant_id=tenant_a.id,
            email=f"admin@{tenant_a.domain}",
            role_slug="admin"
        )
        admin_b = await create_test_user(
            db_session,
            tenant_id=tenant_b.id,
            email=f"admin@{tenant_b.domain}",
            role_slug="admin"
        )
        
        # Create invitations for each tenant
        inv_a = await create_test_invitation(
            db_session,
            tenant_id=tenant_a.id,
            email=f"user@{tenant_a.domain}"
        )
        inv_b = await create_test_invitation(
            db_session,
            tenant_id=tenant_b.id,
            email=f"user@{tenant_b.domain}"
        )
        
        # Admin A lists invitations
        jwt_a = encode_mock_jwt(create_mock_firebase_token(
            uid=admin_a.firebase_uid,
            email=admin_a.email
        ))
        
        response = await api_client.get(
            "/api/b2b/invitations/list",
            headers={"Authorization": f"Bearer {jwt_a}"}
        )
        
        assert response.status_code == 200
        invitations = response.json()
        
        # Should ONLY see invitations from tenant A
        invitation_ids = [inv["id"] for inv in invitations]
        assert str(inv_a.id) in invitation_ids
        assert str(inv_b.id) not in invitation_ids  # Tenant B invitation NOT visible
    
    
    @pytest.mark.asyncio
    async def test_cross_tenant_invitation_cancellation_blocked(
        self,
        api_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Tenant A admin cannot cancel Tenant B's invitation"""
        tenant_a = await create_test_tenant(db_session)
        tenant_b = await create_test_tenant(db_session)
        
        admin_a = await create_test_user(
            db_session,
            tenant_id=tenant_a.id,
            email=f"admin@{tenant_a.domain}",
            role_slug="admin"
        )   
        
        # Create invitation for tenant B
        inv_b = await create_test_invitation(
            db_session,
            tenant_id=tenant_b.id,
            email=f"user@{tenant_b.domain}"
        )
        
        # Admin A tries to cancel tenant B's invitation
        jwt_a = encode_mock_jwt(create_mock_firebase_token(
            uid=admin_a.firebase_uid,
            email=admin_a.email
        ))
        
        response = await api_client.delete(
            f"/api/b2b/invitations/{inv_b.id}",
            headers={"Authorization": f"Bearer {jwt_a}"}
        )
        
        # Should be forbidden
        assert response.status_code == 403
