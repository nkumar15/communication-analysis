# Changelog - 2025-11-26

## UUID Migration & Invitation System Fixes

### Overview
This update completes the UUID migration for the backend codebase and fixes critical issues with the invitation system that prevented new users from joining tenants.

---

## 🔧 Breaking Changes

### UUID Type System
All ID parameters in the backend now use `UUID` type hints instead of `int`. If you have custom code that calls these services, update your type annotations accordingly.

**Affected services:**
- `user_service.py`
- `invitation_service.py`
- `tenant_service.py`
- `permission_checker.py`
- `scope_checker.py`

---

## ✨ Features & Improvements

### 1. Invitation Flow Enhancement
**New users can now successfully accept invitations on first login**

Previously, new invited users would encounter "User not found" errors when attempting to join a tenant after SSO login. This required them to log in twice.

**Changes:**
- `/api/invitations/join` endpoint now creates users from invitations automatically
- No longer requires users to exist in database before accepting invitation
- Single-step process: SSO login → join → dashboard

**Technical Details:**
- Changed from `get_current_active_user` to `get_current_user` dependency
- Extracts user info from Firebase token
- Creates user record with role from invitation if doesn't exist
- Marks invitation as accepted

### 2. Simplified Invitation Endpoints
All invitation management endpoints now use efficient data retrieval:

**Updated endpoints:**
- `POST /api/invitations/invite` - Simplified user lookup
- `GET /api/invitations/list` - Removed redundant database queries
- `DELETE /api/invitations/{id}` - Streamlined permission checks
- `POST /api/invitations/resend/{id}` - Optimized data access

**Benefits:**
- Reduced database queries per request
- Cleaner, more maintainable code
- Better performance

---

## 🐛 Bug Fixes

### 1. Fixed UUID Type Mismatches
**Problem:** Database schema used UUIDs but Python code had `int` type hints, causing validation errors.

**Error Example:**
```
invalid input for query argument $1: 't3mYcMa3UlRXQzKmtwsS49OW8RJ2' 
(invalid UUID 't3mYcMa3UlRXQzKmtwsS49OW8RJ2': length must be between 32..36 characters, got 28)
```

**Solution:** Updated all service and RBAC function signatures to use `UUID` type.

**Files Modified:**
- `app/services/user_service.py`
- `app/services/invitation_service.py`
- `app/services/tenant_service.py`
- `app/rbac/permission_checker.py`
- `app/rbac/scope_checker.py`

### 2. Fixed KeyError in Invitation Endpoints
**Problem:** Endpoints accessed `current_user['id']` but used wrong auth dependency that didn't include database user ID.

**Error:**
```python
KeyError: 'id'
```

**Solution:** Changed to use `get_current_active_user` dependency which includes full user data from database.

### 3. Fixed New User Invitation Acceptance
**Problem:** New users received "User not found" error on first login attempt after SSO authentication.

**Root Cause:** `/join` endpoint required user to exist in database, but new users weren't created until after joining attempt.

**Solution:** Modified `/join` endpoint to handle user creation as part of the join process.

**User Impact:** 
- Before: Required 2 login attempts (first creates user, second works)
- After: Works on first login attempt

---

## 📝 API Changes

### Invitation Join Endpoint

**Endpoint:** `POST /api/invitations/join`

**Before:**
```python
# Required user to exist in database
Depends(get_current_active_user)  # ❌ Failed for new users
```

**After:**
```python
# Works for both new and existing users
Depends(get_current_user)  # ✅ Creates user from invitation if needed
```

**New Behavior:**
1. Validates Firebase token (no database required)
2. Validates invitation token
3. Checks email match
4. **Creates user from invitation if doesn't exist** (NEW)
5. Marks invitation as accepted
6. Returns success

---

## 🔒 Security & Data Integrity

### Row Level Security (RLS)
All changes maintain existing RLS policies:
- User creation automatically scoped to correct tenant
- Invitation validation enforces tenant boundaries
- No cross-tenant data access possible

### Authentication Flow
No changes to authentication security:
- Still uses Firebase JWT validation
- Email verification required
- Invitation token validation maintained
- RBAC permissions enforced

---

## 📊 Database Schema

No database migrations required. All changes are code-level type improvements.

---

## 🧪 Testing

### Verified Scenarios

✅ **New User Invitation Flow:**
1. Admin sends invitation
2. User receives email
3. User clicks link, validates
4. User completes SSO login
5. **User immediately joins tenant** (single attempt)
6. User sees dashboard with correct role

✅ **Existing User Re-invitation:**
1. User already exists with role
2. Admin sends new invitation
3. User logs in and accepts
4. Invitation marked accepted
5. User role preserved (not overwritten)

✅ **UUID Type Validation:**
- All service calls work with UUID parameters
- No type conversion errors
- Database queries execute correctly

✅ **Permission Checks:**
- RBAC functions work with UUID user IDs
- Scope checking operates correctly
- Admin/manager/agent permissions enforced

---

## 🚀 Migration Guide

### For Developers

**No action required** if you're using the API endpoints only.

**If you import services directly** in custom code:

```python
# Before
from app.services.user_service import user_service

user = await user_service.get_user_by_id(db, 123)  # ❌ int

# After
from uuid import UUID
from app.services.user_service import user_service

user = await user_service.get_user_by_id(db, UUID("..."))  # ✅ UUID
```

### For Frontend

**No changes required.** API responses maintain same structure.

---

## 📚 Documentation Updates

- Updated [walkthrough.md](file:///C:/Users/neera/.gemini/antigravity/brain/a2813e59-0ed6-4cec-9038-f2a6b9819779/walkthrough.md) with complete change summary
- Created this CHANGELOG.md
- Updated code comments for clarity

---

## 🙏 Acknowledgments

Thanks for reporting the invitation flow issues. The "works on second login" observation was key to identifying the timing problem.

---

## 📞 Support

If you encounter any issues after this update:

1. Check backend logs: `docker-compose logs backend`
2. Verify invitation flow with test user
3. Review [walkthrough.md](file:///C:/Users/neera/.gemini/antigravity/brain/a2813e59-0ed6-4cec-9038-f2a6b9819779/walkthrough.md) for details

---

**Version:** Backend v1.1.0  
**Date:** November 26, 2025  
**Impact:** Medium (bug fixes, no breaking API changes)
