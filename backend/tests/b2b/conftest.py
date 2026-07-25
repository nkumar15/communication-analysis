"""
B2B Test Suite - Shared Fixtures

This conftest.py provides B2B-specific fixtures that are shared across
all B2B tests (API and Service layers).

Fixture Hierarchy:
  tests/conftest.py          -> db_session, api_client (infra)
  tests/b2b/conftest.py      -> b2b_test_setup, create_test_* helpers (THIS FILE)
  tests/b2b/api/*/conftest.py -> Domain-specific fixtures (optional)
"""
import pytest
import pytest_asyncio
from uuid import uuid4

# Import core fixtures from root conftest
from tests.conftest import (
    # Infrastructure fixtures (re-exported for convenience)
    db_session,
    api_client,
    test_db_engine,
    
    # Helper functions
    create_test_tenant,
    create_test_user,
    create_test_invitation,
    create_mock_firebase_token,
    encode_mock_jwt,
    create_auth_headers,
    set_tenant_context,
    
    # Classes
    TenantAwareSession,
    
    # Other fixtures
    platform_admin_setup,
)


# ============================================================================
# B2B TENANT FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def b2b_tenant(db_session):
    """Create a standard B2B tenant for testing"""
    tenant = await create_test_tenant(db_session)
    return tenant


@pytest_asyncio.fixture
async def b2b_tenant2(db_session):
    """
    Create a SECOND B2B tenant for isolation tests.
    
    Use this fixture when testing RLS (Row-Level Security) to verify
    that Tenant A cannot access Tenant B's data.
    """
    tenant = await create_test_tenant(db_session, domain=f"tenant2-{uuid4().hex[:8]}.test")
    return tenant


@pytest_asyncio.fixture
async def b2b_tenant_owner(db_session, b2b_tenant):
    """Create owner user for b2b_tenant"""
    owner = await create_test_user(
        db_session,
        tenant_id=b2b_tenant.id,
        email=f"owner@{b2b_tenant.domain}",
        role_slug="owner"
    )
    return owner


@pytest_asyncio.fixture
async def b2b_tenant_owner_token(b2b_tenant, b2b_tenant_owner):
    """Create auth token for b2b_tenant owner"""
    return encode_mock_jwt(create_mock_firebase_token(
        uid=b2b_tenant_owner.firebase_uid,
        email=b2b_tenant_owner.email,
        firebase_tenant_id=b2b_tenant.firebase_tenant_id
    ))


# ============================================================================
# B2B TEST SETUP (ALL-IN-ONE FIXTURE)
# ============================================================================

@pytest_asyncio.fixture
async def b2b_test_setup(db_session):
    """
    Complete B2B test setup fixture.
    
    Returns a dict with:
        - tenant: TenantModel
        - tenant_id: UUID
        - owner/admin: UserModel (admin user)
        - token: JWT token for API calls
        - session: TenantAwareSession (auto-sets RLS context)
    
    Usage:
        async def test_my_feature(api_client, b2b_test_setup):
            setup = b2b_test_setup
            headers = {"Authorization": f"Bearer {setup['token']}"}
            response = await api_client.post("/api/b2b/...", headers=headers)
    """
    # Create tenant
    tenant = await create_test_tenant(db_session)
    
    # Create admin user
    admin = await create_test_user(
        db_session,
        tenant_id=tenant.id,
        email=f"admin@{tenant.domain}",
        role_slug="admin"
    )
    
    # Create token
    token = encode_mock_jwt(create_mock_firebase_token(
        uid=admin.firebase_uid,
        email=admin.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    # Create tenant-aware session for DB verification
    tenant_session = TenantAwareSession(db_session, tenant.id)
    
    return {
        "tenant": tenant,
        "tenant_id": tenant.id,
        "owner": admin,  # Legacy alias
        "admin": admin,
        "token": token,
        "session": tenant_session,
    }
