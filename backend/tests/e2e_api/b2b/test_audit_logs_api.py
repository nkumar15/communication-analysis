import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from datetime import datetime, timedelta
from uuid import uuid4

from services.b2b.models.audit_log import AuditLog
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt

@pytest_asyncio.fixture
async def audit_logs_data(db_session):
    """Setup test data with audit logs"""
    # Create tenant and owner
    tenant = await create_test_tenant(db_session)
    owner = await create_test_user(db_session, tenant.id, email="owner@test.com", role_slug="owner")
    
    # Create some logs
    logs = []
    for i in range(5):
        log = AuditLog(
            tenant_id=tenant.id,
            event_type="auth.login" if i % 2 == 0 else "user.invited",
            resource_type="user",
            actor_id=owner.id,
            details={"index": i},
            created_at=datetime.utcnow() - timedelta(hours=i)
        )
        db_session.add(log)
        logs.append(log)
    
    await db_session.commit()
    
    # Generate token
    token = create_mock_firebase_token(
        uid=owner.firebase_uid, 
        email=owner.email, 
        firebase_tenant_id=tenant.firebase_tenant_id
    )
    encoded_token = encode_mock_jwt(token)
    
    return {
        "tenant": tenant,
        "owner": owner,
        "token": encoded_token,
        "logs": logs
    }

@pytest.mark.asyncio
class TestAuditLogsAPI:
    
    async def test_list_audit_logs(self, api_client: AsyncClient, audit_logs_data):
        """Test listing audit logs"""
        headers = {"Authorization": f"Bearer {audit_logs_data['token']}"}
        
        response = await api_client.get("/api/b2b/audit-logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["limit"] == 20

    async def test_filter_audit_logs(self, api_client: AsyncClient, audit_logs_data):
        """Test filtering audit logs"""
        headers = {"Authorization": f"Bearer {audit_logs_data['token']}"}
        
        # Filter by event_type
        response = await api_client.get("/api/b2b/audit-logs?event_type=auth.login", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3  # 0, 2, 4
        assert all(item["event_type"] == "auth.login" for item in data["items"])

    async def test_export_audit_logs(self, api_client: AsyncClient, audit_logs_data):
        """Test exporting audit logs as CSV"""
        headers = {"Authorization": f"Bearer {audit_logs_data['token']}"}
        
        response = await api_client.get("/api/b2b/audit-logs/export", headers=headers)
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        
        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 6  # Header + 5 rows
        assert lines[0].startswith("Date,Event Type,Actor ID")

    async def test_rbac_enforcement(self, api_client: AsyncClient, db_session):
        """Test that non-admins cannot access audit logs"""
        # Create tenant and viewer
        tenant = await create_test_tenant(db_session)
        viewer = await create_test_user(db_session, tenant.id, email="viewer@test.com", role_slug="viewer")
        await db_session.commit()
        
        token = create_mock_firebase_token(
        uid=viewer.firebase_uid, 
        email=viewer.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    )
        encoded_token = encode_mock_jwt(token)
        headers = {"Authorization": f"Bearer {encoded_token}"}
        
        # Try list
        response = await api_client.get("/api/b2b/audit-logs", headers=headers)
        assert response.status_code == 403
        
        # Try export
        response = await api_client.get("/api/b2b/audit-logs/export", headers=headers)
        assert response.status_code == 403
