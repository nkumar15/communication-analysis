# Test Fixture Pattern Fix

## Summary
All factory fixture calls need to pass `db_session` as the **first argument**.

## Files to Update

### 1. test_invitation_flow.py
**Lines to change:**

```python
# Line 28-32: Already fixed ✅
admin = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="admin@test.com",
    role_slug="admin"
)

# Line 64: Fix
tenant = await create_test_tenant(db_session)  # Add db_session

# Line 65-69: Fix
manager = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="manager@test.com",
    role_slug="field_manager"
)

# Line 94: Already needs db_session ✅
tenant = await create_test_tenant(db_session, domain="company.com")

# Line 95-99: Fix
admin = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="admin@company.com",
    role_slug="admin"
)

# Line 124: Fix
tenant = await create_test_tenant(db_session)

# Line 125-128: Fix
invitation = await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="user@test.com"
)

# Line 156: Fix
tenant = await create_test_tenant(db_session)

# Line 157-160: Fix
invitation = await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="newuser@test.com"
)

# Line 202: Fix
tenant = await create_test_tenant(db_session)

# Line 203-206: Fix
invitation = await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="unverified@test.com"
)

# Line 234: Fix
tenant = await create_test_tenant(db_session)

# Line 235-239: Fix
admin = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="admin@test.com",
    role_slug="admin"
)

# Line 242-245: Fix
await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant.id,
    email="user@test.com"
)
```

### 2. test_activation_flow.py
**Already fixed ✅** (line 29)

```python
tenant = await create_test_tenant(db_session, activation_status="pending")
```

**Still need to fix:**

```python
# Line 44-48: Fix
admin = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant.id,
    email=f"admin@{tenant.domain}",
    role_slug="admin"
)

# Line 51-55: Fix
await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant.id,
    email=admin.email,
    role="admin"
)
```

### 3. test_multi_tenant_isolation.py
**All need fixes:**

```python
# Around line 26-29: Fix
tenant_a = await create_test_tenant(
    db_session,  # Add this
    name="Company A",
    domain="companya.com"
)

# Around line 30-33: Fix
tenant_b = await create_test_tenant(
    db_session,  # Add this
    name="Company B",
    domain="companyb.com"
)

# Fix all create_test_user calls:
admin_a = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant_a.id,
    email="admin@companya.com",
    role_slug="admin"
)

admin_b = await create_test_user(
    db_session,  # Add this
    tenant_id=tenant_b.id,
    email="admin@companyb.com",
    role_slug="admin"
)

# Fix all create_test_invitation calls:
inv_a = await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant_a.id,
    email="user@companya.com"
)

inv_b = await create_test_invitation(
    db_session,  # Add this
    tenant_id=tenant_b.id,
    email="user@companyb.com"
)

# Repeat for all other create_test_* calls in that file
```

## Pattern Rule
**Every factory fixture call:**
```python
# OLD (doesn't work):
result = await create_test_X(param1=value1, param2=value2)

# NEW (correct):
result = await create_test_X(db_session, param1=value1, param2=value2)
```

## No Changes Needed For
- `create_mock_firebase_token()` - pure function, no db_session needed
- `encode_mock_jwt()` - pure function, no db_session needed
