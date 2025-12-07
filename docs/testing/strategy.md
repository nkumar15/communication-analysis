# Enterprise SSO - Testing Strategy & Roadmap

This document outlines the current testing infrastructure, how to execute tests, and the roadmap for progressively enhancing test coverage.

## 🚀 Quick Start

Run the full API E2E test suite:
```bash
make e2e-test
```

Run with coverage report:
```bash
make e2e-test-coverage
```

## 📋 Pre-Test Checklist

Before running tests, ensure your environment is ready:

1.  **Services Up**: `make up-backend` (or `make up`) is running.
2.  **Health Check**: `curl http://localhost:8000/health` returns 200.
3.  **Credentials**: `secrets/firebase-credentials.json` exists.
4.  **Database**: `make test-env` reports all configs valid.
5.  **Clean State**: Run `make reset-db` if tests are failing due to stale data.

## 📊 Test Matrix & Coverage

We track functional coverage in the [Test Matrix](./test-matrix.md).
Use this matrix to identify:
- Which API test covers a specific requirement (e.g., `ONB-01`).
- Which Browser test covers the UI flow.
- Gaps where features are implemented but untested.

## 🏗️ Current Infrastructure (Phase 3 Complete)

We have established a robust **API E2E Testing Framework** focusing on security and critical business flows.

### Tech Stack
- **Runner**: `pytest` with `pytest-asyncio`
- **Client**: `httpx` (Async HTTP client)
- **Database**: `sqlalchemy` + `asyncpg` (Direct DB assertions)
- **Mocking**: Custom Firebase Auth mocking (no external dependencies)

### Key Components
| Component | Description | Location |
|-----------|-------------|----------|
| **`conftest.py`** | Shared fixtures (`db_session`, `api_client`) and factories (`create_test_tenant`) | `backend/tests/conftest.py` |
| **`integration/`** | Business flow tests (Invitation, Activation) | `backend/tests/integration/` |
| **`security/`** | Security-specific tests (Isolation, PII, Auth) | `backend/tests/security/` |

### Test Data Strategy
- **Isolation**: Each test runs in a transaction that is rolled back after execution.
- **Randomization**: Tenant domains are randomized (`test-{uuid}.com`) to prevent unique constraint collisions.
- **Factory Pattern**: Use `await create_test_tenant(db_session)` helper functions instead of complex fixture chaining.

## 🗺️ Testing Roadmap (Progressive Enhancement)

We are following a phased approach to testing.

### ✅ Phase 1-3: Foundation (Completed)
- [x] Unit/Integration test harness
- [x] Database transaction isolation
- [x] Critical security flow verification (Invitation/Activation)
- [x] Multi-tenant data isolation checks
- [x] **Platform Admin API Tests** (New)
    - Authentication & Role verification
    - Tenant management (Create/List)
    - Cross-tenant impersonation security

### ✅ Phase 4: Browser E2E Infrastructure (Completed)
**Status**: Infrastructure complete, basic tests passing (3/3 ✅)

**Implemented**:
- ✅ Playwright installed in Docker with system dependencies
- ✅ `frontend` and `e2e-tests` services in docker-compose
- ✅ Sync Playwright API (no async conflicts)
- ✅ Firebase custom token authentication support (real Firebase, no mocks)
- ✅ Test configuration via environment variables
- ✅ Basic page load tests passing

**Scope**:
- `make e2e-browser` - Run browser tests in Docker
- Tests in `backend/tests/e2e_browser/`
- Uses real Firebase GCIP authentication with custom tokens
- Custom token helpers in `e2e_helpers.py`

**Pending** (requires frontend integration + test data setup):
- Platform Admin full workflow (login → create tenant)
- Tenant Activation flow (activation page → SSO → dashboard)
- Invitation flow (join link → accept → login)

**Documentation**: See `backend/tests/e2e_browser/README.md`

### 🔮 Phase 5: Granular RBAC Testing
**Goal**: Verify complex permission matrices beyond simple roles.
- **Scope**:
    - Matrix testing of every permission against every role.
    - API endpoint fuzzing for unauthorized access.
    - Horizontal privilege escalation checks.

### 🔮 Phase 6: Performance & Load Testing
**Goal**: Ensure system handles multi-tenant load.
- **Tool**: k6 or Locust
- **Scope**:
    - Concurrent tenant activation.
    - High-volume invitation acceptance.
    - Database connection pool saturation tests.

---

## 🔒 Multi-Tenant Isolation Testing

### Overview

Multi-tenant isolation is **critical** for security. Our testing strategy ensures:
1. Cross-tenant data access is impossible
2. RLS (Row Level Security) policies work correctly
3. Test fixtures properly respect tenant boundaries

### Testing Architecture

**Key principle:** Tests must mirror production RLS behavior

```python
# ✅ CORRECT Pattern
tenant_a = await create_test_tenant(db_session)  
admin_a = await create_test_user(db_session, tenant_id=tenant_a.id, role_slug="admin")
# RLS context is set inside helper functions

# ❌ WRONG Pattern  
user = UserModel(tenant_id=tenant_a.id, email="test@example.com")
db_session.add(user)
# Missing RLS context = role_id will be None!
```

### RLS Context in Test Fixtures

All test helper functions **must** set RLS context before querying RLS-protected tables:

```python
# CORRECT: conftest.py helper pattern
async def create_test_user(db_session, tenant_id, email, role_slug):
    from sqlalchemy import text, select
    from services.b2b.models import UserModel, Role
    
    # Step 1: Set RLS context FIRST
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    
    # Step 2: Query RLS-protected tables (now safe)
    result = await db_session.execute(
        select(Role).where(Role.name == role_slug, Role.tenant_id == tenant_id)
    )
    role = result.scalar_one_or_none()
    
    # Step 3: Create user with proper role_id
    user = UserModel(tenant_id=tenant_id, email=email, role_id=role.id)
    db_session.add(user)
    await db_session.flush()
    return user
```

### Isolation Test Patterns

#### Pattern 1: List Endpoint Isolation

**Verify:** Tenant A cannot see Tenant B's resources

```python
@pytest.mark.security
async def test_cross_tenant_resource_listing_blocked(api_client, db_session):
    # Arrange: Two tenants with data
    tenant_a = await create_test_tenant(db_session, name="Company A")
    tenant_b = await create_test_tenant(db_session, name="Company B")
    
    admin_a = await create_test_user(db_session, tenant_id=tenant_a.id, role_slug="admin")
    
    # Create resource for tenant B
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_b.id}'"))
    resource_b = Resource(tenant_id=tenant_b.id, name="Tenant B Resource")
    db_session.add(resource_b)
    await db_session.flush()
    
    # Act: Admin A lists resources
    jwt_a = encode_mock_jwt(create_mock_firebase_token(
        uid=admin_a.firebase_uid,
        email=admin_a.email,
        firebase_tenant_id=tenant_a.firebase_tenant_id
    ))
    
    response = await api_client.get("/api/b2b/resources", headers={"Authorization": f"Bearer {jwt_a}"})
    
    # Assert: Tenant B's resource is invisible
    assert response.status_code == 200
    resources = response.json()
    resource_ids = [r["id"] for r in resources]
    assert str(resource_b.id) not in resource_ids  # ✅ Isolation enforced
```

#### Pattern 2: Direct Access Isolation

**Verify:** Tenant A cannot access Tenant B's resource by ID

```python
@pytest.mark.security
async def test_cross_tenant_resource_access_by_id_blocked(api_client, db_session):
    # Arrange
    tenant_a = await create_test_tenant(db_session)
    tenant_b = await create_test_tenant(db_session)
    
    admin_a = await create_test_user(db_session, tenant_id=tenant_a.id, role_slug="admin")
    
    # Create resource for tenant B
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_b.id}'"))
    resource_b = Resource(tenant_id=tenant_b.id, name="Secret Resource")
    db_session.add(resource_b)
    await db_session.flush()
    
    # Act: Admin A tries to access tenant B's resource by ID
    jwt_a = create_test_jwt(admin_a)
    response = await api_client.get(
        f"/api/b2b/resources/{resource_b.id}",
        headers={"Authorization": f"Bearer {jwt_a}"}
    )
    
    # Assert: Returns 404 (not 403 - doesn't leak existence)
    assert response.status_code == 404  # ✅ Resource appears non-existent
```

#### Pattern 3: Mutation Isolation

**Verify:** Tenant A cannot modify/delete Tenant B's resource

```python
@pytest.mark.security
async def test_cross_tenant_resource_deletion_blocked(api_client, db_session):
    tenant_a = await create_test_tenant(db_session)
    tenant_b = await create_test_tenant(db_session)
    
    admin_a = await create_test_user(db_session, tenant_id=tenant_a.id, role_slug="admin")
    
    # Create resource for tenant B
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_b.id}'"))
    resource_b = Resource(tenant_id=tenant_b.id, name="Protected Resource")
    db_session.add(resource_b)
    await db_session.flush()
    
    # Act: Admin A tries to delete tenant B's resource
    jwt_a = create_test_jwt(admin_a)
    response = await api_client.delete(
        f"/api/b2b/resources/{resource_b.id}",
        headers={"Authorization": f"Bearer {jwt_a}"}
    )
    
    # Assert: Deletion fails (404)
    assert response.status_code == 404
    
    # Verify: Resource still exists in tenant B
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_b.id}'"))
    result = await db_session.execute(select(Resource).where(Resource.id == resource_b.id))
    assert result.scalar_one_or_none() is not None  # ✅ Still exists
```

### Testing Checklist for New Features

When adding a new RLS-protected feature, write these tests:

- [ ] **List Isolation**: Tenant A cannot list Tenant B's resources
- [ ] **Get Isolation**: Tenant A cannot get Tenant B's resource by ID (returns 404)
- [ ] **Create Isolation**: Created resources automatically belong to caller's tenant
- [ ] **Update Isolation**: Tenant A cannot update Tenant B's resource (returns 404)
- [ ] **Delete Isolation**: Tenant A cannot delete Tenant B's resource (returns 404)
- [ ] **Relationship Isolation**: Related entities (e.g., team members) respect tenant boundaries

### Test Data Cleanup

**Important:** Use transaction rollback for isolation cleanup

```python
# conftest.py pattern (already implemented)
@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncSession:
    """Create a fresh database session for each test"""
    async_session_factory = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        await session.begin()  # Start transaction
        try:
            yield session
        finally:
            await session.rollback()  # ✅ Automatic cleanup
```

### Common Test Failures & Solutions

#### Issue: `role_id` is None in created users

**Symptom:**
```
INFO ... has_permission: user=<UserModel>, user.role_id=None
INFO ... has_permission: No user or role_id found, returning False
```

**Cause:** RLS context not set before querying `roles` table in `create_test_user`

**Solution:**
```python
# Move SET LOCAL before role query
await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
result = await db_session.execute(select(Role).where(Role.name == role_slug))
```

#### Issue: Expected 403, got 404

**This is correct!** RLS makes cross-tenant resources appear non-existent (404), not forbidden (403). Update test expectations:

```python
# ✅ CORRECT
assert response.status_code == 404  # RLS makes it invisible

# ❌ WRONG
assert response.status_code == 403  # Leaks that resource exists
```

#### Issue: `IntegrityError: duplicate key value violates unique constraint`

**Cause:** Static domain reuse across tests

**Solution:** Use randomized domains (already in helpers):
```python
# ✅ Automatically generates unique domain
tenant = await create_test_tenant(db_session, name="Test Company")
# domain will be: test-{uuid}.com
```

### TenantAwareSession Pattern

For advanced testing scenarios, use `TenantAwareSession` wrapper:

```python
# Available in conftest.py
class TenantAwareSession:
    """Automatically manages tenant context for all DB operations"""
    
    async def execute(self, *args, **kwargs):
        # Automatically sets RLS context before each query
        await self._ensure_context()
        return await self._session.execute(*args, **kwargs)

# Usage in tests
tenant_session = TenantAwareSession(db_session, tenant.id)
result = await tenant_session.execute(select(User))  # RLS auto-applied
```

---

## 📖 Troubleshooting & Lookup

### Common Issues

**`IntegrityError: duplicate key value violates unique constraint`**
- **Cause**: Reusing the same static domain (e.g., "test.com") across tests without rollback working correctly, or parallel execution issues.
- **Fix**: Use the randomized domain feature in factories: `create_test_tenant(db_session)` (generates random domain automatically).

**`403 Forbidden` in Permission Tests**
- **Cause**: User created without proper role assignment due to RLS context timing
- **Fix**: Ensure `create_test_user` sets RLS context before querying roles table

**`404 Not Found` in Isolation Tests (Expected 403)**
- **This is correct!** RLS makes cross-tenant resources invisible (404), not forbidden (403)
- **Fix**: Update test expectations to `assert response.status_code == 404`

**`MissingGreenlet` Error**
- **Cause**: Accessing lazy-loaded relationships (like `tenant.users`) in an async context without explicit loading.
| Command | Purpose |
|---------|---------|
| `pytest tests/integration` | Run only integration tests |
| `pytest -m security` | Run only tests marked as `@pytest.mark.security` |
| `pytest -k "invitation"` | Run tests matching substring "invitation" |
| `pytest --pdb` | Drop into debugger on failure |

---

## 🛡️ Security & Middleware Testing (Critical)

**Lesson Learned:** Do not bypass security middleware in tests.

### ❌ Dangerous Pattern: Middleware Overrides
**NEVER** override the core authentication/authorization middleware (`get_current_active_user`) in `conftest.py` just to simplify tests. 

**Why?**
- It hides security logic bugs (e.g., missing activation checks, banned user checks).
- Tests will pass even if the production security logic is broken or missing.
- It creates a false sense of security.

**Wrong:**
```python
# conftest.py
async def override_get_current_active_user():
    # Simplistic lookup that skips checks
    return {"id": "user-1", "role": "admin"} # 🚨 DANGEROUS!

app.dependency_overrides[get_current_active_user] = override_get_current_active_user
```

### ✅ Correct Pattern: Mock Dependencies, Not Logic
Mock the **external dependencies** (like token verification), but let the **internal logic** run.

**Correct:**
1.  Override `get_current_user` (the token verifier) to accept mock tokens.
2.  Let `get_current_active_user` (the user resolver) run normally.
3.  It will receive the mock token payload and execute all real DB lookups and security checks.

```python
# conftest.py
app.dependency_overrides[get_current_user] = override_verify_token # ✅ Safe
# Do NOT override get_current_active_user
```

### Validation Checklist for Security Tests
- [ ] **Pending Tenants**: ensure unactivated tenants cannot access API.
- [ ] **Wrong Invitations**: ensure User A cannot accept User B's invitation.
- [ ] **Email Mismatch**: ensure activating user matches the invited admin email.
- [ ] **Cross-Tenant**: ensure Tenant A cannot see Tenant B's data (RLS).
