# B2B E2E Activation Flow Test Guide

Complete walkthrough for testing the B2B tenant activation process.

**Last Updated:** 2025-12-20  
**Status:** ✅ Fully Automated (API) | ⚠️ Manual (Browser)

---

## Overview

The tenant activation flow consists of 5 main steps:
1. **Platform Admin** creates tenant and sends invitation
2. **Tenant Owner** receives email with activation link
3. **Owner** validates activation token
4. **Owner** authenticates via SSO
5. **Owner** completes activation

**Documentation:**
- Specification: [`docs/specifications/tenant-onboarding.md`](../specifications/tenant-onboarding.md)
- Architecture: [`docs/architecture/b2b/tenant-onboarding-flow.md`](../architecture/b2b/tenant-onboarding-flow.md)

---

## Prerequisites

1. **Backend running** (port 8080)
2. **Frontend running** (port 3000)
3. **Firebase project** with multi-tenancy enabled
4. **Test OIDC provider** configured (Auth0/Okta test account)

### Check Status
```bash
docker-compose ps           # Backend should be "Up"
cd frontend && npm start    # Frontend on port 3000
```

---

## Method 1: Automated API Testing (Recommended)

### Run Activation Tests

```bash
# Full activation test suite
make test-api FILTER="test_activation"

# Specific tests
docker-compose run --rm e2e-tests pytest \
  tests/e2e_api/b2b/onboarding/test_activation.py -v

# Platform onboarding tests
docker-compose run --rm e2e-tests pytest \
  tests/e2e_api/platform/test_tenant_onboarding.py -v
```

### Test Coverage

**Covered Scenarios:**
- ✅ Valid activation token flow
- ✅ Expired token rejection
- ✅ Already activated tenant
- ✅ Invalid token format
- ✅ Tenant status transitions
- ✅ Owner user creation
- ✅ Default team assignment
- ✅ Multi-provider support

---

## Method 2: Manual Browser Testing

### Step 1: Create Test Tenant

**Option A: Using Make Command**
```bash
make reset-db
```

**Option B: Using Platform API** (Preferred for production-like testing)
```bash
# 1. Get platform admin token (from platform app login)
PLATFORM_TOKEN="your_platform_admin_jwt_token"

# 2. Create tenant via API
curl -X POST http://localhost:8080/api/platform/b2b/tenants/onboard \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "domain": "testcompany.com",
    "owner_email": "admin@testcompany.com"
  }'
```

**Expected Response:**
```json
{
  "tenant_id": "uuid",
  "tenant_name": "Test Company",
  "domain": "testcompany.com",
  "owner_email": "admin@testcompany.com",
  "firebase_tenant_id": "testcompany-xxxxx",
  "activation_url": "http://localhost:3000/activate/{token}",
  "activation_token": "secret_token",
  "expires_at": "2025-12-22T10:00:00Z"
}
```

**Copy the `activation_url`** from the response!

---

### Step 2: Open Activation Link

Paste the activation URL in your browser:
```
http://localhost:3000/activate/{token}
```

**Expected Flow:**

#### Screen 1: Validating Token
- Loading spinner
- "Validating activation link..."
- API calls `/api/public/activate/validate/{token}`

#### Screen 2: Welcome Screen
- 🎉 Welcome message
- Company name displayed: "Test Company"
- Admin email shown: "admin@testcompany.com"
- Domain shown: "testcompany.com"
- **"Get Started →"** button

---

### Step 3: Begin Activation

Click **"Get Started"**

**What Happens:**
1. Frontend fetches tenant's Firebase config
2. Frontend calls `GET /api/b2b/activate/tenant-info/{tenant_id}`
3. Firebase OIDC login popup opens
4. You complete SSO login with test provider

**Expected:**
- Firebase authentication popup opens
- You log in with your SSO provider (Auth0/Okta/etc)
- Popup closes automatically
- Firebase ID token received

---

### Step 4: SSO Login Success

After successful SSO login:

#### Screen 3: SSO Verified
- ✅ SSO Login Successful!
- "Your single sign-on is working correctly"
- Firebase UID displayed
- **"Activate Account"** button

---

### Step 5: Complete Activation

Click **"Activate Account"**

**What Happens:**
1. Frontend calls `POST /api/activate/complete`
2. Backend validates token + Firebase ID token
3. Backend executes atomic transaction:
   - Updates `tenant.activation_status = 'active'`
   - Creates owner user record
   - Assigns Owner role
   - Adds user to Default Team
   - Marks invitation as accepted
4. Frontend redirects to `/dashboard`

**Expected:**
- Success message displayed
- Redirect to B2B dashboard
- You're logged in as tenant owner!

---

## Verification

### Database State Check

After completing activation:

```bash
# Check tenant status
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, name, domain, activation_status, activation_expires_at FROM b2b.tenants ORDER BY created_at DESC LIMIT 5;"

# Check owner user
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, email, firebase_uid, role_id, is_active FROM b2b.users ORDER BY created_at DESC LIMIT 5;"

# Check invitation
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, email, role, accepted_at FROM b2b.invitations ORDER BY created_at DESC LIMIT 5;"

# Check default team
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, name, is_default FROM b2b.teams ORDER BY created_at DESC LIMIT 5;"
```

### Expected Results

**Tenants Table:**
```
id                  | name         | domain          | activation_status | activation_expires_at
--------------------+--------------+-----------------+-------------------+---------------------
uuid-here...        | Test Company | testcompany.com | active            | NULL (was set, now NULL)
```

**Users Table:**
```
id           | email                  | firebase_uid | role_id      | is_active
-------------+------------------------+--------------+--------------+-----------
uuid-here... | admin@testcompany.com  | FirebaseUID  | owner-role-id| true
```

**Invitations Table:**
```
id           | email                  | role  | accepted_at
-------------+------------------------+-------+--------------------
uuid-here... | admin@testcompany.com  | owner | 2025-12-20 10:30:00
```

**Teams Table:**
```
id           | name          | is_default
-------------+---------------+------------
uuid-here... | Default Team  | true
```

---

## Common Issues & Solutions

### Issue: "Invalid activation token"

**Possible Causes:**
- Token expired (>48 hours)
- Token already used
- Token malformed

**Solutions:**
```bash
# Check token expiration in database
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, domain, activation_expires_at, activation_status FROM b2b.tenants WHERE id = 'tenant-uuid';"

# Resend activation (Platform Admin only)
curl -X POST http://localhost:8080/api/platform/b2b/tenants/{tenant_id}/resend \
  -H "Authorization: Bearer $PLATFORM_TOKEN"
```

---

### Issue: "Tenant not found" or 404

**Causes:**
- Tenant ID doesn't exist
- RLS context not set for public endpoint

**Verification:**
```bash
# Check if tenant exists
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id, domain FROM b2b.tenants;"
```

---

### Issue: "Organization has been deactivated"

**Cause:** Tenant's `is_active = false`

**Solution:**
```bash
# Reactivate tenant (Platform Admin only)
curl -X PATCH http://localhost:8080/api/platform/b2b/tenants/{tenant_id}/reactivate \
  -H "Authorization: Bearer $PLATFORM_TOKEN"
```

---

### Issue: SSO Popup Doesn't Open

**Causes:**
- Browser blocking popups
- Firebase tenant ID incorrect
- OIDC provider not configured

**Solutions:**
1. **Allow popups** in browser settings
2. **Verify Firebase config**:
   ```bash
   # Check tenant's Firebase tenant ID
   docker-compose exec postgres psql -U sso_user -d sso_db -c \
     "SELECT firebase_tenant_id FROM b2b.tenants WHERE domain = 'testcompany.com';"
   ```
3. **Check OIDC provider**:
   ```bash
   docker-compose exec postgres psql -U sso_user -d sso_db -c \
     "SELECT provider_id, provider_type FROM b2b.auth_providers WHERE tenant_id = 'uuid';"
   ```

---

### Issue: "User already exists with different email"

**Cause:** Firebase UID collision (extremely rare)

**Solution:** Use different test email address

---

## Quick Test Script

```bash
#!/bin/bash
# Full E2E activation test

# 1. Reset database
make reset-db

# 2. Create tenant via CLI (interactive)
# Follow prompts to enter:
# - Company name
# - Domain
# - Owner email
# - Firebase tenant ID (if reusing)
# - OIDC provider ID

# 3. Copy activation URL from output

# 4. Open in browser
echo "Open this URL in your browser:"
echo "http://localhost:3000/activate/TOKEN_FROM_OUTPUT"

# 5. Complete flow in browser
echo "Steps:"
echo "  1. Click 'Get Started'"
echo "  2. Complete SSO login"
echo "  3. Click 'Activate Account'"

# 6. Verify in database
echo "Verifying..."
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT name, activation_status FROM b2b.tenants ORDER BY created_at DESC LIMIT 1;"
```

---

## Success Criteria

✅ Activation link validates successfully  
✅ Welcome screen shows correct tenant info  
✅ SSO login completes without errors  
✅ Firebase ID token received  
✅ User record created with real Firebase UID  
✅ Owner role assigned  
✅ Default team created  
✅ Invitation marked as accepted  
✅ Tenant status = 'active'  
✅ Activation token cleared  
✅ Redirected to dashboard  
✅ Can access protected B2B routes  

---

## Next Steps After Successful Activation

1. **Invite team members** via `/organization/invite`
2. **Create teams** for organizational structure
3. **Configure SSO providers** (SAML, Google, etc.)
4. **Set up billing** (upgrade to Professional/Enterprise)
5. **Test multi-user collaboration**

---

## Automated Test Reference

The API test suite covers all activation scenarios:

```python
# Location: tests/e2e_api/b2b/onboarding/test_activation.py

class TestActivationFlow:
    async def test_validate_valid_token(self):
        """Token validation returns tenant info"""
        
    async def test_validate_expired_token(self):
        """Expired tokens return 410 Gone"""
        
    async def test_complete_activation_success(self):
        """Full activation flow completes successfully"""
        
    async def test_complete_activation_creates_user(self):
        """User record created with correct role"""
        
    async def test_complete_activation_marks_invitation_accepted(self):
        """Invitation accepted_at timestamp set"""
        
    async def test_tenant_status_becomes_active(self):
        """activation_status changes to 'active'"""
```

**Run all activation tests:**
```bash
docker-compose run --rm e2e-tests pytest \
  tests/e2e_api/b2b/onboarding/test_activation.py -v
```

---

**Ready to test!** 🚀

For detailed architecture, see [`docs/architecture/b2b/tenant-onboarding-flow.md`](../architecture/b2b/tenant-onboarding-flow.md)
