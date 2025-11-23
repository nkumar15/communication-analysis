# End-to-End Activation Flow Test Guide

Complete walkthrough for testing the tenant activation process.

---

## Prerequisites

1. **Backend running** (port 8000)
2. **Frontend running** (port 3000)
3. **Firebase tenant created** (or reuse existing)

Check status:
```bash
docker-compose ps  # Backend should be Up
# Frontend: cd frontend && npm start
```

---

## Testing Steps

### Step 1: Create Test Tenant

Run the interactive reset script:

```bash
make reset-db
```

**When prompted, enter:**
- Create tenant? **y**
- Firebase Tenant ID: `firstcompany-99oyw` (your existing one)
- OIDC Provider ID: `oidc.oidc.auth0.firstcompany` (or your OIDC provider)
- Company Name: `First Company`
- Domain: `firstcompany.net`
- Admin Email: `admin01@firstcompany.net`

**Expected Output:**
```
================================================================================
📧 ACTIVATION EMAIL (Fallback to console)
================================================================================
ACTIVATION URL (Copy this to browser):

    http://localhost:3000/activate/TOKEN_HERE

Expires: 2025-11-25 13:46 UTC
================================================================================
```

**Copy the activation URL!**

---

### Step 2: Start Frontend (if not running)

```bash
cd frontend
npm start
```

Waits for: `Compiled successfully!`

---

### Step 3: Open Activation Link

Paste the activation URL in your browser:
```
http://localhost:3000/activate/TOKEN_HERE
```

**Expected Flow:**

#### Screen 1: Validating
- Loading spinner
- "Validating activation link..."

#### Screen 2: Welcome
- 🎉 Welcome message
- Company name displayed
- Admin email shown
- Domain shown
- **"Get Started →"** button

---

### Step 4: Click "Get Started"

**What happens:**
1. Frontend fetches Firebase tenant config
2. Opens Firebase OIDC login popup
3. You log in with your SSO provider (Auth0/Okta/etc)

**Expected:**
- Firebase authentication popup opens
- You complete SSO login
- Popup closes
- User record created in database

---

### Step 5: SSO Login Success

After successful SSO login:

#### Screen 3: Success
- ✅ SSO Login Successful!
- "Your single sign-on is working correctly"
- **"Activate Account"** button

---

### Step 6: Complete Activation

Click **"Activate Account"**

**What happens:**
1. Frontend calls `/api/activate/complete`
2. Backend marks invitation as accepted
3. Backend activates tenant
4. Redirects to dashboard

**Expected:**
- Redirect to `/dashboard`
- You're logged in!

---

## Verification

### Database State Check

After completing activation:

```bash
# Check tenant status
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "SELECT id, name, activation_status, activated_at FROM tenants;"

# Check invitation
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "SELECT id, email, accepted_at FROM invitations;"

# Check user
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "SELECT id, email, role, firebase_uid FROM users;"
```

**Expected Results:**

**Tenants:**
```
id | name          | activation_status | activated_at
----+---------------+-------------------+-------------
 1 | First Company | active            | 2025-11-23...
```

**Invitations:**
```
id | email                  | accepted_at
----+------------------------+-------------
 1 | admin01@firstcompany.net | 2025-11-23...
```

**Users:**
```
id | email                  | role  | firebase_uid
----+------------------------+-------+-------------
 1 | admin01@firstcompany.net | admin | xyz123abc...
```

---

## Common Issues

### Issue: "Invalid activation token"
**Cause:** Token expired or already used
**Fix:** Run `make reset-db` again to get a new token

### Issue: Frontend shows 404
**Cause:** Frontend route not configured
**Fix:** Check App.js has `/activate/:token` route

### Issue: CORS error
**Cause:** Frontend can't reach backend
**Fix:** Check backend is on port 8000, frontend on 3000

### Issue: "Tenant already activated"
**Cause:** Testing same tenant twice
**Fix:** Use different domain or reset DB

### Issue: SSO popup doesn't open
**Cause:** Popup blocked or Firebase config wrong
**Fix:** 
- Allow popups in browser
- Check Firebase tenant ID is correct
- Verify OIDC provider configured

---

## Quick Test Script

```bash
# 1. Reset and create tenant
make reset-db
# Enter your details when prompted

# 2. Copy activation URL from output

# 3. Open in browser
# Paste URL: http://localhost:3000/activate/TOKEN

# 4. Click through:
#    - Get Started
#    - Complete SSO login
#    - Activate Account

# 5. Verify in database
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT name, activation_status FROM tenants;"
```

---

## Success Criteria

✅ Activation link validates successfully
✅ Welcome screen shows correct tenant info
✅ SSO login completes without errors
✅ User record created with real Firebase UID
✅ Invitation marked as accepted
✅ Tenant status changed to 'active'
✅ Redirected to dashboard
✅ Can access protected routes

---

## Next Steps After Successful Test

1. **Invite additional users** (managers/members)
2. **Test multi-user scenarios**
3. **Configure production email** (Resend API)
4. **Deploy to staging**
5. **Production rollout**

---

**Last Updated:** 2025-11-23
**Ready to test!** 🚀
