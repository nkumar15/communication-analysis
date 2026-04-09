import pytest
from httpx import AsyncClient
from modules.platform.middleware.platform_auth import RequirePlatformPermission

# We need to mock the verify_platform_admin dependency to return specific permissions
# or create a user with specific permissions in the DB.
# For E2E, it's better to use the DB.

@pytest.mark.asyncio
async def test_permission_wildcard_logic():
    """Unit test for the logic itself"""
    checker = RequirePlatformPermission("tenants", "read")
    
    # helper
    def check(perms):
        return checker._has_permission(perms)

    # 1. Exact match
    assert check([{"resource": "tenants", "action": "read"}]) is True
    
    # 2. Wrong action
    assert check([{"resource": "tenants", "action": "write"}]) is False
    
    # 3. Wrong resource
    assert check([{"resource": "users", "action": "read"}]) is False
    
    # 4. Resource Wildcard
    assert check([{"resource": "*", "action": "read"}]) is True
    
    # 5. Action Wildcard
    assert check([{"resource": "tenants", "action": "*"}]) is True
    
    # 6. Full Wildcard
    assert check([{"resource": "*", "action": "*"}]) is True
