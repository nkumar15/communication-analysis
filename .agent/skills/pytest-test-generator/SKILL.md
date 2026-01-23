---
name: pytest-test-generator
description: Generate pytest test cases for API endpoints following established patterns.
---

# Pytest Test Generator

When asked to generate tests cases for feature, generate test cases for routers and services layers of the feature.

## 0. Decision Matrix (Router vs Service)
Use this matrix to resolve ambiguity on where to place a test:

| Scenario | Test at Layer |
| :--- | :--- |
| **Business rule** | Service |
| **RBAC decision** | Service |
| **Team scope validation** | Service |
| **Data visibility logic** | Service |
| **HTTP status code** | API |
| **Auth dependency** | API |
| **Request validation** | API |
| **JSON shape** | API |
| **Service exception mapping** | API |

## 1. Determine Test Location

### Directory Structure
```
backend/tests/
├── conftest.py                   # ROOT: Core fixtures ONLY (db_session, api_client)
├── b2b/
│   ├── conftest.py               # B2B SHARED: b2b_test_setup, helpers, TenantAwareSession
│   ├── api/
│   │   ├── foundation/           # API tests for core B2B (auth, teams, users, billing)
│   │   └── use_cases/
│   │       ├── bank_surveillance/ # API tests for Bank domain
│   │       └── task_management/   # API tests for Task domain
│   └── services/
│       ├── foundation/           # Service tests for core B2B logic
│       └── use_cases/
│           ├── bank_surveillance/ # Service tests for Bank logic
│           └── task_management/   # Service tests for Task logic
├── e2e_api/                      # Legacy/B2C/Platform
│   ├── b2c/
│   └── platform/
├── e2e_browser/                  # Playwright browser tests
├── units/                        # Pure unit tests (no DB)
└── load/                         # Performance/stress tests
```

## 2. Fixture Hierarchy

| Layer | Location | What it Provides |
| :--- | :--- | :--- |
| **1. Root** | `tests/conftest.py` | `db_session`, `api_client`, `mock_stripe` (infra-level) |
| **2. B2B Shared** | `tests/b2b/conftest.py` | `b2b_test_setup`, `create_test_tenant`, `create_test_user`, `TenantAwareSession` |
| **3. Use-Case** | `tests/b2b/api/bank_surveillance/conftest.py` | Domain-specific fixtures (`bank_tenant`, `alert_fixture`) |

### Standard Fixtures
- **B2B Tests**: Use `b2b_test_setup`. Compose from `b2b_tenant`, `b2b_tenant_owner` for isolation tests.
- **Platform Tests**: Use `platform_admin_setup`.
- **B2C Tests**: Use `b2c_user_setup`.

### Multi-Tenant Isolation (`b2b_tenant2`)
`b2b_tenant2` is a fixture for creating a **second tenant** to test RLS (Row-Level Security) isolation. It is NOT a duplicate—it's essential for verifying that Tenant A cannot see Tenant B's data.

```python
# Example: Tenant Isolation Test
async def test_tenant_isolation(api_client, b2b_test_setup, b2b_tenant2):
    # b2b_tenant2 is a DIFFERENT tenant
    other_user = await create_test_user(session, tenant_id=b2b_tenant2.id, ...)
    # Verify that other_user cannot see b2b_test_setup's data
```

## 3. API Layer Testing (Thin Router)

### What to test in API Layer (thin router)
API tests validate:
- **Routing**
- **Auth wiring**
- **Dependency injection**
- **Serialization / deserialization**
- **HTTP status codes**
- **Policy enforcement boundaries**

> [!IMPORTANT]
> You do **NOT** retest business logic here.

### Example API test
```python
@pytest.mark.asyncio
async def test_assign_role_endpoint(api_client, b2b_test_setup):
    """Test role assignment endpoint wiring"""
    # Arrange
    setup = b2b_test_setup
    headers = {"Authorization": f"Bearer {setup['token']}"}
    payload = {"role_id": "analyst", "team_id": "india"}
    
    # Act
    response = await api_client.post(
        "/api/b2b/users/123/roles", # Example path
        json=payload,
        headers=headers
    )

    # Assert
    assert response.status_code == 200
```

### Minimal API test set (recommended)
For each router, generate:
- 1 happy path
- 1 auth failure (401)
- 1 permission failure (403)
- 1 validation error (400)

### Template
```python
"""
Tests for {endpoint_name} endpoint
Path: {endpoint_path}
"""
import pytest
from fastapi import status


class Test{ResourceAction}:
    """Tests for {verb} {resource}"""

    @pytest.mark.asyncio
    async def test_{action}_success(self, api_client, b2b_test_setup):
        """Happy path: Valid input and permissions"""
        # Arrange
        headers = {"Authorization": f"Bearer {b2b_test_setup['token']}"}
        payload = {...}
        
        # Act
        response = await api_client.{method}(
            "{endpoint_path}",
            json=payload,
            headers=headers
        )
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED  # or appropriate
        data = response.json()
        assert data["name"] == payload["name"]

    @pytest.mark.asyncio
    async def test_{action}_unauthorized(self, api_client):
        """No token should return 401"""
        response = await api_client.{method}("{endpoint_path}", json={...})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_{action}_forbidden(self, api_client, b2b_test_setup, db_session):
        """Wrong role should return 403"""
        # Create user with insufficient permissions
        from tests.conftest import create_test_user, create_auth_headers
        viewer = await create_test_user(
            db_session,
            tenant_id=b2b_test_setup['tenant_id'],
            role_slug="viewer"
        )
        headers = create_auth_headers(viewer, b2b_test_setup['tenant'])
        
        response = await api_client.{method}("{endpoint_path}", json={...}, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_{action}_not_found(self, api_client, b2b_test_setup):
        """Invalid resource ID should return 404"""
        headers = {"Authorization": f"Bearer {b2b_test_setup['token']}"}
        response = await api_client.{method}(
            "{endpoint_path}/00000000-0000-0000-0000-000000000000",
            headers=headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_{action}_tenant_isolation(self, api_client, b2b_test_setup, b2b_tenant2):
        """Should not access other tenant's resources"""
        # b2b_tenant2 is a different tenant
        from tests.conftest import create_test_user, create_auth_headers
        other_owner = await create_test_user(...)  # in b2b_tenant2
        headers = create_auth_headers(other_owner, b2b_tenant2)
        
        # Try to access resource from b2b_test_setup's tenant
        response = await api_client.get(
            f"{endpoint_path}/{b2b_test_setup_resource_id}",
            headers=headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND  # RLS blocks
```

## 4. Service Layer Testing (Logic Tests)

### What to test in Service Layer (fat logic)
✅ ALWAYS test services when:
- **Permissions / RBAC logic**
- **State transitions**
- **Business rules**
- **Multi-step workflows**
- **Validation logic**
- **Side effects** (events, audit logs)
- **Error conditions**

### Example service test
```python
@pytest.mark.asyncio
async def test_assign_role_to_user_in_team(db_session, b2b_test_setup):
    """Test role assignment logic in service layer"""
    # Arrange
    setup = b2b_test_setup
    user = setup["owner"]
    session = setup["session"]
    
    # Act
    from modules.b2b.services.role_service import role_service
    # ... logic to assign role ...
    
    # Assert
    # Verify business logic outcomes
    assert ... 
```

## 5. DB Verification Pattern (Integration Verification)
For stateful operations, verify DB state:
```python
# After API call, verify DB using tenant-aware session
session = b2b_test_setup['session']
result = await session.execute(
    select(Model).where(Model.id == created_id)
)
db_record = result.scalar_one()
assert db_record.name == expected_name
```

## 6. Parameterization (Power Tool)
### Parameterization = power tool
Use it aggressively for RBAC.

```python
@pytest.mark.parametrize(
    "role_scope, team_scope, expected",
    [
        ("GLOBAL", "GLOBAL", True),
        ("GLOBAL", "COUNTRY", False),
        ("COUNTRY", "COUNTRY", True),
    ]
)
async def test_role_scope_validation(role_scope, team_scope, expected):
    assert can_assign(role_scope, team_scope) == expected
```

## 7. Checklist Before Delivery
- [ ] Router tests include all 4 minimal cases (Happy, 401, 403, 400)
- [ ] Service tests cover complex logic (State, Rules, Transitions)
- [ ] Uses existing fixtures from conftest (no reinventing)
- [ ] AAA pattern followed
- [ ] No hardcoded UUIDs/emails (use uuid4/unique suffixes)
- [ ] RLS context handled correctly
