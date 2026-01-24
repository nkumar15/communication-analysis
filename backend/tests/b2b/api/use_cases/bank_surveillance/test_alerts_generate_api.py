"""
API Tests for Alerts Generate Endpoint

Tests POST /alerts/generate endpoint routing, auth, and async job handling.
"""
import pytest
from fastapi import status


class TestGenerateAlerts:
    """Tests for POST /alerts/generate endpoint."""
    
    @pytest.mark.asyncio
    async def test_generate_alerts_success(self, api_client, b2b_test_setup, db_session):
        """Happy path: Trigger alert generation with valid auth."""
        setup = b2b_test_setup
        from sqlalchemy import text
        
        # Grant permission (Bypass RLS)
        from modules.b2b.models.rbac import Resource, Action, RolePermission, Role
        from sqlalchemy import select
        
        await db_session.execute(text("SET app.is_platform_admin = 'true'"))
        user = setup["owner"]
        if user not in db_session:
             user = await db_session.merge(user)
        await db_session.refresh(user)
        
        # Create role if missing
        if not user.role_id:
             role = Role(tenant_id=user.tenant_id, name="owner", display_name="Owner")
             db_session.add(role)
             await db_session.flush()
             user.role_id = role.id
             db_session.add(user)
             await db_session.flush()
             await db_session.refresh(user)
        
        # Resource
        res = await db_session.execute(select(Resource).where(Resource.name == "alerts"))
        resource = res.scalar_one_or_none()
        if not resource:
            resource = Resource(name="alerts", display_name="Alerts", category="Domain")
            db_session.add(resource)
            await db_session.flush()
            
        # Action
        res = await db_session.execute(select(Action).where(Action.name == "write"))
        action = res.scalar_one_or_none()
        if not action:
            action = Action(name="write", display_name="Write")
            db_session.add(action)
            await db_session.flush()
            
        # RolePermission
        res = await db_session.execute(select(RolePermission).where(
            RolePermission.role_id == user.role_id,
            RolePermission.resource_id == resource.id,
            RolePermission.action_id == action.id
        ))
        if not res.scalar_one_or_none():
            rp = RolePermission(role_id=user.role_id, resource_id=resource.id, action_id=action.id)
            db_session.add(rp)
            await db_session.commit()
            
        await db_session.execute(text("SET app.is_platform_admin = 'false'"))

        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/alerts/generate",
            json={},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data
    
    @pytest.mark.asyncio
    async def test_generate_alerts_with_date_range(self, api_client, b2b_test_setup, db_session):
        """Test alert generation with date range filter."""
        setup = b2b_test_setup
        from sqlalchemy import text
        
        # Grant permission (Bypass RLS)
        from modules.b2b.models.rbac import Resource, Action, RolePermission, Role
        from sqlalchemy import select
        
        await db_session.execute(text("SET app.is_platform_admin = 'true'"))
        user = setup["owner"]
        if user not in db_session:
             user = await db_session.merge(user)
        await db_session.refresh(user)
        
        # Create role if missing
        if not user.role_id:
             role = Role(tenant_id=user.tenant_id, name="owner", display_name="Owner")
             db_session.add(role)
             await db_session.flush()
             user.role_id = role.id
             db_session.add(user)
             await db_session.flush()
             await db_session.refresh(user)
        
        # Resource
        res = await db_session.execute(select(Resource).where(Resource.name == "alerts"))
        resource = res.scalar_one_or_none()
        if not resource:
            resource = Resource(name="alerts", display_name="Alerts", category="Domain")
            db_session.add(resource)
            await db_session.flush()
            
        # Action
        res = await db_session.execute(select(Action).where(Action.name == "write"))
        action = res.scalar_one_or_none()
        if not action:
            action = Action(name="write", display_name="Write")
            db_session.add(action)
            await db_session.flush()
            
        # RolePermission
        res = await db_session.execute(select(RolePermission).where(
            RolePermission.role_id == user.role_id,
            RolePermission.resource_id == resource.id,
            RolePermission.action_id == action.id
        ))
        if not res.scalar_one_or_none():
            rp = RolePermission(role_id=user.role_id, resource_id=resource.id, action_id=action.id)
            db_session.add(rp)
            await db_session.commit()
            
        await db_session.execute(text("SET app.is_platform_admin = 'false'"))
        
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/alerts/generate",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            headers=headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.asyncio
    async def test_generate_alerts_unauthorized(self, api_client):
        """No token should return 401."""
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/alerts/generate",
            json={}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_generate_alerts_forbidden_viewer(self, api_client, b2b_test_setup, db_session):
        """Viewer role should return 403 (write permission required)."""
        from tests.conftest import create_test_user, encode_mock_jwt, create_mock_firebase_token
        
        setup = b2b_test_setup
        
        # Create viewer user
        viewer = await create_test_user(
            db_session,
            tenant_id=setup["tenant_id"],
            email=f"viewer-{setup['tenant_id'].hex[:8]}@test.com",
            role_slug="viewer"
        )
        
        viewer_token = encode_mock_jwt(create_mock_firebase_token(
            uid=viewer.firebase_uid,
            email=viewer.email,
            firebase_tenant_id=setup["tenant"].firebase_tenant_id
        ))
        
        headers = {"Authorization": f"Bearer {viewer_token}"}
        
        response = await api_client.post(
            "/api/b2b/domain/bank_surveillance/alerts/generate",
            json={},
            headers=headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
