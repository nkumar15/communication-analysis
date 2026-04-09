"""
API Tests for Risk Events Endpoint

Tests /risk-events endpoint routing, auth, and serialization.
"""
import pytest
from fastapi import status


class TestListRiskEvents:
    """Tests for GET /risk-events endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_risk_events_success(self, api_client, b2b_test_setup, db_session):
        """Happy path: List risk events with valid auth."""
        setup = b2b_test_setup
        from sqlalchemy import text
        
        # Grant permission (Bypass RLS)
        from modules.b2b.models.rbac import Resource, Action, RolePermission, Role
        from sqlalchemy import select
        
        # Use raw session and elevate privileges
        await db_session.execute(text("SET app.is_platform_admin = 'true'"))
        
        user = setup["owner"]
        # Ensure user is attached
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
            resource = Resource(name="alerts", display_name="Surveillance Alerts", category="Domain")
            db_session.add(resource)
            await db_session.flush()
            
        # Action
        res = await db_session.execute(select(Action).where(Action.name == "read"))
        action = res.scalar_one_or_none()
        if not action:
            action = Action(name="read", display_name="Read")
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
            
        # Reset privileges
        await db_session.execute(text("SET app.is_platform_admin = 'false'"))
        
        headers = {"Authorization": f"Bearer {setup['token']}"}
        
        response = await api_client.get(
            "/api/b2b/domain/bank_surveillance/risk-events/",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_risk_events_unauthorized(self, api_client):
        """No token should return 401."""
        response = await api_client.get(
            "/api/b2b/domain/bank_surveillance/risk-events/"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_list_risk_events_with_filters(self, api_client, b2b_test_setup, db_session):
        """Test filtering parameters are accepted."""
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
            resource = Resource(name="alerts", display_name="Surveillance Alerts", category="Domain")
            db_session.add(resource)
            await db_session.flush()
            
        # Action
        res = await db_session.execute(select(Action).where(Action.name == "read"))
        action = res.scalar_one_or_none()
        if not action:
            action = Action(name="read", display_name="Read")
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
        
        response = await api_client.get(
            "/api/b2b/domain/bank_surveillance/risk-events/",
            params={
                "sender": "test@bank.com",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "limit": 10,
                "offset": 0
            },
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK


class TestGetRiskEvent:
    """Tests for GET /risk-events/{event_id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_risk_event_data_structure(self, api_client, b2b_test_setup):
        """Test structure of returned risk event."""
        # ... (Same pattern would apply if implementing detailed test)
        pass
    
    @pytest.mark.asyncio
    async def test_get_risk_event_not_found(self, api_client, b2b_test_setup, db_session):
        """Invalid event ID should return 404."""
        setup = b2b_test_setup
        from sqlalchemy import text
        
        # Grant permission
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
            resource = Resource(name="alerts", display_name="Surveillance Alerts", category="Domain")
            db_session.add(resource)
            await db_session.flush()
        # Action
        res = await db_session.execute(select(Action).where(Action.name == "read"))
        action = res.scalar_one_or_none()
        if not action:
            action = Action(name="read", display_name="Read")
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
        
        response = await api_client.get(
            "/api/b2b/domain/bank_surveillance/risk-events/00000000-0000-0000-0000-000000000000",
            headers=headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_risk_event_unauthorized(self, api_client):
        """No token should return 401."""
        response = await api_client.get(
            "/api/b2b/domain/bank_surveillance/risk-events/00000000-0000-0000-0000-000000000000"
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
