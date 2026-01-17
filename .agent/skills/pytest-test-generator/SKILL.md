---
name: pytest-test-generator
description: Generate pytest test cases for API endpoints following established patterns.
---

# Pytest Test Generator

When asked to generate tests for an endpoint, follow these steps:

## 1. Determine Test Location
- B2B endpoint -> `backend/tests/e2e_api/b2b/{feature_area}/`
- B2C endpoint -> `backend/tests/e2e_api/b2c/`
- Platform endpoint -> `backend/tests/e2e_api/platform/`

## 2. Analyze Required Fixtures
- **B2B Tests**: Use `b2b_test_setup` or compose from `b2b_tenant`, `b2b_tenant_owner`.
- **Platform Tests**: Use `platform_admin_setup`.
- **B2C Tests**: Use `b2c_user_setup` or compose from `b2c_user`, `b2c_workspace`.

## 3. Generate Test Cases
Always include these minimum cases:

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

## 4. DB Verification Pattern
For stateful operations, verify DB state:
```python
# After API call, verify DB
session = b2b_test_setup['session']
result = await session.execute(
    select(Model).where(Model.id == created_id)
)
db_record = result.scalar_one()
assert db_record.name == expected_name
```

## 5. Checklist Before Delivery
- [ ] All 5 standard test cases present
- [ ] Uses existing fixtures from conftest (no reinventing)
- [ ] AAA pattern followed
- [ ] No hardcoded UUIDs/emails (use uuid4/unique suffixes)
- [ ] RLS context handled correctly
