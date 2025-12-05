import pytest
import pytest_asyncio
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from services.b2b.models.audit_log import AuditLog
from tests.conftest import create_test_tenant, create_test_user, create_mock_firebase_token, encode_mock_jwt

@pytest_asyncio.fixture(autouse=True)
async def patch_audit_service_session(test_db_engine):
    """Patch AuditService to use test_db_engine (same loop)"""
    from services.b2b.services import audit_service
    
    original = audit_service.AsyncSessionLocal
    audit_service.AsyncSessionLocal = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    yield
    
    audit_service.AsyncSessionLocal = original

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
    # Re-fetch to attach to session if needed, or just delete by ID
    # Simpler to just delete by ID using delete statement if we had it, 
    # but here we can just use the object if it's attached, or fetch and delete.
    # Since we committed, the object might be detached or expired.
    
    # Let's just delete by ID
    from sqlalchemy import delete
    await db_session.execute(
        delete(TenantModel).where(TenantModel.id == tenant.id)
    )
    await db_session.commit()

@pytest.mark.asyncio
class TestAuditLogs:
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
        
        # 2. Check audit logs
        # Note: Background tasks might take a moment, but in tests they usually run synchronously 
        # or we might need to wait/retry if strictly async. 
        # However, FastAPI TestClient usually handles BackgroundTasks by running them.
        await asyncio.sleep(1)
        
        query = select(AuditLog).where(
            AuditLog.tenant_id == b2b_test_data['tenant_id'],
            AuditLog.event_type == "user.invited"
        ).order_by(AuditLog.created_at.desc())
        
        result = await db_session.execute(query)
        log = result.scalar_one_or_none()
        
        assert log is not None
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
        
        # 2. Check audit logs
        await asyncio.sleep(2)
        query = select(AuditLog).where(
            AuditLog.tenant_id == b2b_test_data['tenant_id']
        ).order_by(AuditLog.created_at.desc())
        
        result = await db_session.execute(query)
        logs = result.scalars().all()
        
        # Filter for auth.login
        log = next((l for l in logs if l.event_type == "auth.login"), None)
        
        if not log:
            print(f"DEBUG: Found {len(logs)} logs: {[l.event_type for l in logs]}")
        
        assert log is not None
        assert log.resource_type == "user"
        assert str(log.actor_id) == str(b2b_test_data['owner_id'])
        assert log.details['method'] == "sso_sync"
