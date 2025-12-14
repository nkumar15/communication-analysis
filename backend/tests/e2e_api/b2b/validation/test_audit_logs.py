
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from services.b2b.models.audit_log import AuditLog
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt
from datetime import datetime, timedelta

@pytest_asyncio.fixture
async def b2b_test_data(db_session):
    """Setup basic B2B test data (Tenant + Owner) - COMMITTED for Background Tasks"""
    # 1. Create Tenant
    tenant = await create_test_tenant(db_session)
    
    # 2. Create Owner
    owner = await create_test_user(
        db_session, 
        tenant.id, 
        f"owner@{tenant.domain}", 
        role_slug="owner"
    )
    
    # COMMIT so background tasks (separate transaction) can see FKs
    await db_session.commit()
    
    # 3. Generate Token
    token_payload = create_mock_firebase_token(
        uid=owner.firebase_uid,
        email=owner.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    )
    owner_token = encode_mock_jwt(token_payload)
    
    yield {
        "tenant_id": tenant.id,
        "tenant_domain": tenant.domain,
        "owner_id": owner.id,
        "owner_email": owner.email,
        "owner_token": owner_token
    }
    
    # Cleanup
    # We need to delete the tenant which cascades to users and audit logs
    from services.b2b.models import TenantModel
    await db_session.execute(
        select(TenantModel).where(TenantModel.id == tenant.id)
    )
    
    from sqlalchemy import delete
    await db_session.execute(
        delete(TenantModel).where(TenantModel.id == tenant.id)
    )
    await db_session.commit()

@pytest_asyncio.fixture
async def audit_logs_api_data(db_session):
    """Setup test data with audit logs for API testing"""
    # Create tenant and owner
    tenant = await create_test_tenant(db_session)
    owner = await create_test_user(db_session, tenant.id, email="owner_logs@test.com", role_slug="owner")
    
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
class TestAuditLogCreation:
    """Test that actions trigger audit logs"""

    async def test_audit_log_created_on_invite(self, api_client, b2b_test_data, db_session):
        """Test that inviting a user creates an audit log"""
        
        # 1. Invite a user
        response = await api_client.post(
            "/api/b2b/invitations/invite",
            headers={"Authorization": f"Bearer {b2b_test_data['owner_token']}"},
            json={
                "email": f"audit_test@{b2b_test_data['tenant_domain']}",
                "role": "viewer"
            }
        )
        assert response.status_code == 200
        
        # 2. Check audit logs (Poll for async task completion)
        
        query = select(AuditLog).where(
            AuditLog.tenant_id == b2b_test_data['tenant_id'],
            AuditLog.event_type == "user.invited"
        ).order_by(AuditLog.created_at.desc())
        
        log = None
        from tests.conftest import set_tenant_context
        
        for _ in range(20):  # Retry 20 times (wait up to 4s for engine spin-up)
            await db_session.commit() # End current transaction to see new data
            
            # CRITICAL: Must set RLS context to see rows!
            await set_tenant_context(db_session, b2b_test_data['tenant_id'])
            
            result = await db_session.execute(query)
            log = result.scalar_one_or_none()
            if log:
                break
            await asyncio.sleep(0.2)
        
        assert log is not None, "Audit log not found after polling"
        assert log.resource_type == "invitation"
        assert str(log.actor_id) == str(b2b_test_data['owner_id'])
        assert log.details['email'] == f"audit_test@{b2b_test_data['tenant_domain']}"

    async def test_audit_log_created_on_sync_user(self, api_client, b2b_test_data, db_session):
        """Test that syncing a user (login) creates an audit log"""
        
        # 1. Call sync-user (simulating login)
        response = await api_client.post(
            "/api/b2b/auth/sync-user",
            headers={"Authorization": f"Bearer {b2b_test_data['owner_token']}"}
        )
        assert response.status_code == 200
        
        # 2. Verify audit log created in DB (Poll for async task completion)
        query = select(AuditLog).where(
            AuditLog.tenant_id == b2b_test_data['tenant_id'],
            AuditLog.event_type == "auth.login"
        ).order_by(AuditLog.created_at.desc())
        
        log = None
        from tests.conftest import set_tenant_context
        
        for _ in range(20):
            await db_session.commit() # Refresh snapshot
            
            # CRITICAL: Must set RLS context
            await set_tenant_context(db_session, b2b_test_data['tenant_id'])
            
            result = await db_session.execute(query)
            log = result.scalar_one_or_none()
            if log:
                break
            await asyncio.sleep(0.2)
        
        assert log is not None, "Audit log not found after polling"
        assert log.resource_type == "user"
        assert str(log.actor_id) == str(b2b_test_data['owner_id'])
        assert log.details["method"] == "sso_sync"

@pytest.mark.asyncio
class TestAuditLogsAPI:
    """Test retrieving audit logs via API"""
    
    async def test_list_audit_logs(self, api_client: AsyncClient, audit_logs_api_data):
        """Test listing audit logs"""
        headers = {"Authorization": f"Bearer {audit_logs_api_data['token']}"}
        
        response = await api_client.get("/api/b2b/audit-logs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["limit"] == 20

    async def test_filter_audit_logs(self, api_client: AsyncClient, audit_logs_api_data):
        """Test filtering audit logs"""
        headers = {"Authorization": f"Bearer {audit_logs_api_data['token']}"}
        
        # Filter by event_type
        response = await api_client.get("/api/b2b/audit-logs?event_type=auth.login", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3  # 0, 2, 4
        assert all(item["event_type"] == "auth.login" for item in data["items"])

    async def test_export_audit_logs(self, api_client: AsyncClient, audit_logs_api_data):
        """Test exporting audit logs as CSV"""
        headers = {"Authorization": f"Bearer {audit_logs_api_data['token']}"}
        
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

    async def test_filter_audit_logs_by_date_range(self, api_client: AsyncClient, audit_logs_api_data):
        """Test filtering audit logs by date range"""
        headers = {"Authorization": f"Bearer {audit_logs_api_data['token']}"}
        
        # Logs are created at [now, now-1h, now-2h, now-3h, now-4h]
        # Let's filter for last 2.5 hours (should get 3 logs: 0, 1, 2)
        
        start_date = (datetime.utcnow() - timedelta(hours=2.5)).isoformat()
        end_date = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        
        response = await api_client.get(
            f"/api/b2b/audit-logs?start_date={start_date}&end_date={end_date}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 3
        # Indices 0, 1, 2 should be returned (created 0h, 1h, 2h ago)
        indices = [log["details"]["index"] for log in data["items"]]
        assert sorted(indices) == [0, 1, 2]

    async def test_filter_audit_logs_by_actor(self, api_client: AsyncClient, audit_logs_api_data):
        """Test filtering audit logs by actor_id"""
        headers = {"Authorization": f"Bearer {audit_logs_api_data['token']}"}
        owner_id = str(audit_logs_api_data['owner'].id)
        
        response = await api_client.get(f"/api/b2b/audit-logs?actor_id={owner_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 5  # All created by owner
        assert all(item["actor_id"] == owner_id for item in data["items"])
