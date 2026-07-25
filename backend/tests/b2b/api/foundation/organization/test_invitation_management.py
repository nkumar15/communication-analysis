"""
E2E Tests for Invitation Management (Resend/Cancel)
"""
import pytest
from httpx import AsyncClient
from modules.b2b.services.invitation_service import invitation_service
from core.constants import B2BRoleName
from datetime import datetime, timedelta, timezone

pytestmark = pytest.mark.asyncio

class TestInvitationManagement:
    """Test resending and cancelling invitations"""

    async def test_resend_invitation_success(
        self,
        api_client: AsyncClient,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test resending an invitation"""
        # Create an initial invitation
        # We need to manually create it or use fixture, but simplest is via API or service
        # Using service to ensure it exists in DB committed
        
        inv, _ = await invitation_service.invite_user_to_tenant(
            db=db_session,
            tenant_id=b2b_tenant.id,
            email=f"resend@{b2b_tenant.domain}",
            role=B2BRoleName.MEMBER,
            invited_by_user_id=None, # System invite for test simplicity? Or need valid ID?
            current_user_role="owner"
            # Service might fail if invited_by_user_id is None and it checks FK? 
            # Tenant service usually requires invited_by.
        )
        # Actually create_test_user is better source of ID
        from tests.conftest import create_test_user
        owner = await create_test_user(db_session, b2b_tenant.id, role_slug="owner", email=f"owner2@{b2b_tenant.domain}")
        inv.invited_by = owner.id
        db_session.add(inv)
        await db_session.commit()
        
        response = await api_client.post(
            f"/api/b2b/invitations/resend/{inv.id}",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        assert f"Invitation resent to {inv.email}" in response.json()["message"]

    async def test_cancel_invitation_success(
        self,
        api_client: AsyncClient,
        db_session,
        b2b_tenant,
        b2b_tenant_owner_token
    ):
        """Test cancelling a pending invitation"""
        from tests.conftest import create_test_user
        owner = await create_test_user(db_session, b2b_tenant.id, role_slug="owner", email=f"owner3@{b2b_tenant.domain}")

        # Create invitation
        inv, _ = await invitation_service.invite_user_to_tenant(
            db=db_session,
            tenant_id=b2b_tenant.id,
            email=f"cancel@{b2b_tenant.domain}",
            role=B2BRoleName.MEMBER,
            invited_by_user_id=owner.id,
            current_user_role="owner"
        )
        await db_session.commit()
        
        response = await api_client.delete(
            f"/api/b2b/invitations/{inv.id}",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
        
        # Verify it's gone or marked deleted? 
        # API says "cancel/delete", usually means hard delete or soft delete.
        # Let's check status via list
        list_response = await api_client.get(
            "/api/b2b/invitations/list",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        ids = [i["id"] for i in list_response.json()]
        assert str(inv.id) not in ids

    async def test_resend_nonexistent_invitation(
        self,
        api_client: AsyncClient,
        b2b_tenant_owner_token
    ):
        """Test resending invalid ID"""
        from uuid import uuid4
        random_id = uuid4()
        
        response = await api_client.post(
            f"/api/b2b/invitations/resend/{random_id}",
            headers={"Authorization": f"Bearer {b2b_tenant_owner_token}"}
        )
        
        assert response.status_code == 404
