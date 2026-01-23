---
trigger: always_on
---

# Pytest Testing Rules

## Scope
Owned by: **QA Lead / Senior Developer**
Applies to: **All test code in `backend/tests/`**

## 0. Execution Environment
**CRITICAL**: Tests must **ALWAYS** be run inside the Docker container to ensure access to DB, Redis, and other services.
- **Do NOT** run `pytest` directly on the host machine.
- **Use Make**: `make test-api` or `make test-coverage`
- **Use Docker**: `docker compose run --rm e2e-tests pytest <path_to_test>`
- **Output redirection**: always redirect test cases output to file for debugging and validation of test cases 
## 1. Test Organization

### Directory Structure
```
backend/tests/
├── conftest.py                   # ROOT: Core fixtures ONLY (db_session, api_client)
├── b2b/                          # B2B Module Tests
│   ├── conftest.py               # B2B SHARED: b2b_test_setup, helpers
│   ├── api/
│   │   ├── foundation/           # Core B2B (Auth, Teams, Billing)
│   │   └── use_cases/            # Domain B2B (Bank, Task Management)
│   ├── services/
│   │   ├── foundation/ 
│   │   └── use_cases/
│   └── units/                    # Pure unit tests (no DB) for B2B
│       └── plugins/              # Plugin-specific logic tests
├── b2c/                          # B2C Module Tests
│   ├── conftest.py               # B2C SHARED: b2c_billing_user, etc.
│   ├── api/
│   │   ├── foundation/           # Core B2C (Workspaces, Auth)
│   │   └── use_cases/            # Domain B2C (Finance Trader, etc.)
│   ├── services/
│   └── units/                    # Pure unit tests (no DB) for B2C
├── platform/                     # Platform Module Tests
│   ├── api/                      # Platform API tests
│   ├── services/                 # Platform Service tests
│   └── units/                    # Pure unit tests (no DB) for Platform
├── e2e_browser/                  # Playwright browser tests
└── load/                         # Performance/stress tests
```

### Naming Conventions
- Test files: `test_{feature}.py`
- Test classes: `Test{FeatureName}` (e.g. `TestRBACAuthorization`)
- Test functions: `test_{action}_{scenario}` (e.g., `test_create_team_unauthorized`)
- Fixtures: `{entity}_fixture` or `{module}_{entity}` (e.g., `b2b_tenant_owner`)

### Class-Based Organization
Tests MUST be grouped into classes to improve readability and fixture scoping.
```python
class TestTeamManagement:
    async def test_create_team(self, api_client):
        ...
```

## 2. Fixture Hierarchy

### Rule: Compose, Don't Duplicate
- **Root `conftest.py`**: Core fixtures (`db_session`, `api_client`, `b2b_test_setup`).
- **Module `conftest.py`**: Module-specific fixtures that BUILD on root fixtures.
- **Test file fixtures**: Only for highly localized, single-test data.

### Standard Fixtures
| Fixture | Purpose | Returns |
|---------|---------|---------|
| `db_session` | Fresh DB session per test | `AsyncSession` |
| `api_client` | HTTPX client with dependency overrides | `AsyncClient` |
| `b2b_test_setup` | Tenant + Admin + Token + TenantAwareSession | `dict` |
| `platform_admin_setup` | Platform tenant + Admin + Token | `dict` |

### Usage Pattern
```python
async def test_my_feature(api_client, b2b_test_setup):
    setup = b2b_test_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # API Call
    response = await api_client.post("/api/...", json={...}, headers=headers)
    
    # DB Verification (using tenant-aware session)
    result = await setup['session'].execute(select(Model).where(...))
```

## 3. AAA Pattern (Arrange-Act-Assert)

Every test **MUST** follow this structure:
```python
async def test_example(api_client, b2b_test_setup):
    # Arrange - Setup test data
    setup = b2b_test_setup
    ...
    
    # Act - Perform the action under test
    response = await api_client.post(...)
    
    # Assert - Verify outcomes
    assert response.status_code == status.HTTP_201_CREATED
    ...
```

## 4. RLS Context Handling

### Problem: RLS can mask bugs if context bleeds between tests.

### Rule: Use `TenantAwareSession` for DB verification
```python
# In b2b_test_setup fixture
tenant_session = TenantAwareSession(db_session, tenant.id)
return {"session": tenant_session, ...}

# In test
result = await setup['session'].execute(select(Team).where(Team.id == team_id))
```

### Rule: Use `set_tenant_context()` for manual context setting
```python
from tests.conftest import set_tenant_context

await set_tenant_context(db_session, tenant.id)
```

## 5. Mock Authentication

### Rule: Use helper functions, not raw token strings
```python
from tests.conftest import create_auth_headers, create_test_user

user = await create_test_user(session, tenant_id=tenant.id, role_slug="admin")
headers = create_auth_headers(user, tenant)
```

## 6. Test Isolation

### Rule: Tests MUST NOT share mutable state
- Each test gets a fresh `db_session` (rolled back after test).
- Use unique identifiers (e.g., `f"user-{uuid4().hex[:8]}@test.com"`).
- Avoid global variables in fixtures.

## 7. Minimum Test Cases per Endpoint

| Case | Description |
|------|-------------|
| `_success` | Happy path with valid input and permissions |
| `_unauthorized` | No token (401) |
| `_forbidden` | Valid token, wrong permission (403) |
| `_not_found` | Invalid resource ID (404) |
| `_validation_error` | Invalid input payload (400/422) |
| `_tenant_isolation` | Other tenant's data not accessible (404 or empty) |

## 8. Role Usage & Domain Isolation

### Rule: Use Domain-Specific Roles for Use Case Features
**CRITICAL**: System roles (`owner`, `member`, `admin`, `viewer`) MUST NOT be used to test use case features (e.g., Bank Surveillance, Marketing Agency). These roles are reserved for testing core B2B SaaS platform features.


### Example: Use Case Role Assignment
```python
async def setup_rbac(self, setup):
    """Assign domain-specific role to the test user."""
    db = setup["session"]
    user_id = setup["owner"].id
    
    # Correct: Use use-case roles like 'surveillance_chief'
    # Incorrect: Using 'owner' or 'admin' for bank features
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    role = (await db.execute(
        select(TeamRoleDefinition).where(TeamRoleDefinition.name == "surveillance_chief")
    )).scalars().first()
    
    # Assign to user...
```

## 9. Asyncio Configuration (CRITICAL)

### Problem: Scope Mismatch causing RuntimeError
Using `session`-scoped fixtures (like `test_db_engine`) with default `pytest-asyncio` settings causes `RuntimeError: Task attached to a different loop`. This is because tests run in a Function-Scoped loop, but the DB engine was created in a (closed) Session Setup loop.

### Rule: Enforce Session-Scoped Event Loop
**DO NOT** manually define an `event_loop` fixture in `conftest.py`. Instead, configure `pytest.ini` to align the loop scope with your fixtures.

**`backend/pytest.ini`**:
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
```
This ensures ALL async fixtures and tests share the same event loop lifecycle.

## 10. Test commands and docker : Look at Makefile for docker commands
Always look at makefile to identify relevant test commands and execute
if you see any network failures or inconsistent container states, ALWAYS prune, recreate services and network for fresh start

## 11. Test Ratio Policy

For each new feature or service, maintain the following test distribution:

| Layer | Ratio | Location |
|-------|-------|----------|
| **Unit** | 50% | `tests/{module}/units/` |
| **Service** | 30% | `tests/{module}/services/` |
| **API** | 20% | `tests/{module}/api/` |

### Guidelines
- **Unit tests**: No DB, no I/O. Mock all dependencies. Fast (<50ms each).
- **Service tests**: Real DB session. Test business logic isolation.
- **API tests**: Full request/response cycle. Test auth + RBAC.

### When to Prioritize
- New service → Start with Service tests
- New plugin → Start with Unit tests
- New endpoint → Add corresponding API test

### Middleware/Plugin Testing
When plugins enforce access control at the API layer via middleware:
1. **Unit tests** verify plugin logic in isolation
2. **Service tests** verify plugin + DB interactions
3. **API tests** verify the full middleware enforcement (request → plugin → response)

