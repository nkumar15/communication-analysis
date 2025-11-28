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

## 📖 Troubleshooting & Lookup

### Common Issues

**`IntegrityError: duplicate key value violates unique constraint`**
- **Cause**: Reusing the same static domain (e.g., "test.com") across tests without rollback working correctly, or parallel execution issues.
- **Fix**: Use the randomized domain feature in factories: `create_test_tenant(db_session)` (generates random domain automatically).

**`403 Forbidden` in Invitation Tests**
- **Cause**: Mismatch between the invited email and the mock JWT email, or `email_verified` claim is missing.
- **Fix**: Ensure `create_mock_firebase_token` email matches the invitation exactly and `email_verified=True`.

**`MissingGreenlet` Error**
- **Cause**: Accessing lazy-loaded relationships (like `tenant.users`) in an async context without explicit loading.
- **Fix**: Use `await db_session.refresh(obj, attribute_names=["users"])` or eager loading options.

### Command Reference
| Command | Purpose |
|---------|---------|
| `pytest tests/integration` | Run only integration tests |
| `pytest -m security` | Run only tests marked as `@pytest.mark.security` |
| `pytest -k "invitation"` | Run tests matching substring "invitation" |
| `pytest --pdb` | Drop into debugger on failure |
