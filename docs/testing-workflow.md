# Tenant Onboarding & Testing Workflow

Complete guide for tenant provisioning and activation testing.

---

## Quick Reference

### CLI Commands

```bash
# Full tenant setup (creates Firebase + DB)
docker-compose exec backend python -m cli.tenant_cli create \
  --company "CompanyName" \
  --domain "company.com" \
  --admin-email "admin@company.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "your_client_id" \
  --oidc-client-secret "your_secret" \
  --oidc-issuer "https://company.auth0.com"

# Quick testing (reuse existing Firebase tenant)
docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "YourTenant-abc123" \
  --oidc-provider-id "oidc.auth0" \
  --company "TestCompany" \
  --domain "test.com" \
  --admin-email "admin@test.com"

# List tenants
docker-compose exec backend python -m cli.tenant_cli list-tenants --domain company.com
```

### Makefile Commands

```bash
make reset-db    # Interactive DB reset + optional tenant creation
make migrate     # Run migrations only
make restart     # Restart services
make clean       # Stop and remove all containers
```

---

## Complete Workflow

### 1. First-Time Setup (Production)

**Creates everything from scratch:**

```bash
# Step 1: Create tenant with Firebase + OIDC + DB
docker-compose exec backend python -m cli.tenant_cli create \
  --company "Acme Corporation" \
  --domain "acme.com" \
  --admin-email "admin@acme.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "actual_client_id" \
  --oidc-client-secret "actual_secret" \
  --oidc-issuer "https://acme.auth0.com"
```

**What happens:**
1. ✅ Creates Firebase tenant in Google Cloud Identity Platform
2. ✅ Configures OIDC provider automatically via REST API
3. ✅ Generates secure activation token (48-hour expiry)
4. ✅ Creates tenant record in database
5. ✅ Creates admin invitation
6. ✅ Sends activation email (or logs to console)

**Output:**
```
Firebase Tenant:  AcmeCorporation-abc123
OIDC Provider:    oidc.auth0
Activation URL:   http://localhost:3000/activate/TOKEN
```

**Save these for testing!** ⚠️

---

### 2. Quick Testing Workflow

**For repeated testing (reuses Firebase):**

#### Option A: Interactive Script

```bash
# Run interactive reset
make reset-db
# or
./reset-db.sh
```

**Prompts you for:**
- Create tenant now? (y/n)
- Firebase Tenant ID
- OIDC Provider ID
- Company Name
- Domain
- Admin Email

#### Option B: Manual Commands

```bash
# 1. Reset database
make reset-db

# 2. Create local tenant (when prompted, say 'n')
docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "AcmeCorporation-abc123" \
  --oidc-provider-id "oidc.auth0" \
  --company "AcmeTest" \
  --domain "acme.com" \
  --admin-email "admin@acme.com"
```

**What happens (fast!):**
1. ✅ Generates new activation token
2. ✅ Creates tenant in DB (reuses Firebase tenant)
3. ✅ Creates admin invitation
4. ✅ Logs activation URL to console

**Skips:** Firebase tenant creation, OIDC configuration (already exists)

---

## Activation Flow

### Admin Receives Email

The activation email contains:
```
Activation URL: http://localhost:3000/activate/TOKEN
Expires: 2025-11-25 12:00 UTC
```

### Step-by-Step Activation

1. **Admin clicks activation link**
   - Frontend: `GET /api/activate/validate/{token}`
   - Validates token, shows welcome screen

2. **Admin clicks "Get Started"**
   - Frontend: `GET /api/activate/tenant-info/{tenant_id}`
   - Gets Firebase tenant ID & OIDC provider
   - Initiates Firebase OIDC login (popup)

3. **Admin logs in via SSO**
   - Firebase handles OIDC authentication
   - User created in Firebase on first login
   - Backend creates user record in DB
   - Frontend: `POST /api/auth/sync-user`

4. **Admin clicks "Activate Account"**
   - Frontend: `POST /api/activate/complete`
   - Backend marks invitation as accepted
   - Backend activates tenant
   - Redirect to dashboard

---

## Database State Transitions

### Initial State (After CLI)
```
tenants:
  activation_status: 'pending'
  activation_token: 'abc123...'

invitations:
  accepted_at: NULL

users:
  (empty - no users yet)
```

### After SSO Login
```
tenants:
  activation_status: 'pending' (still)

invitations:
  accepted_at: NULL (still)

users:
  firebase_uid: 'xyz789...' (real UID)
  role: 'admin'
```

### After Activation Complete
```
tenants:
  activation_status: 'active'
  activation_token: NULL (cleared)
  activated_at: timestamp
  activated_by: user.id

invitations:
  accepted_at: timestamp

users:
  (unchanged)
```

---

## Testing Scenarios

### Scenario 1: Fresh Full Setup
```bash
# Create everything from scratch
docker-compose exec backend python -m cli.tenant_cli create ...
# Copy Firebase tenant ID from output
# Use for future testing
```

### Scenario 2: Repeated Testing (Same Tenant)
```bash
# Reset DB
make reset-db

# Reuse Firebase tenant
docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "SavedTenant-abc123" \
  --oidc-provider-id "oidc.auth0" \
  ...

# Copy new activation URL from console
# Test activation flow
```

### Scenario 3: Multiple Tenants (Same Firebase)
```bash
# Create different domains, same Firebase tenant
docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "SharedTenant-abc123" \
  --domain "companyA.com" ...

docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "SharedTenant-abc123" \
  --domain "companyB.com" ...
```

---

## Important Notes

### Firebase Tenant Management

- **Firebase tenants are NOT deleted** by reset-db.sh
- They persist in Google Cloud Identity Platform
- **Reuse them for testing** to avoid quota limits
- Manual cleanup in Firebase Console if needed

### Firebase Users

- **Users created during SSO login**, not by CLI
- Persist in Firebase even after DB reset
- Can be reused or deleted in Firebase Console
- Local DB user records are wiped on reset

### Activation Tokens

- **48-hour expiry** by default
- **Single-use** (cleared after activation)
- **New token generated** on each `create-local` run
- Old tokens become invalid after DB reset

### Email Service

- **Falls back to console** if `RESEND_API_KEY` not set
- Look for boxed output with activation URL
- Copy URL to test activation flow
- Set `RESEND_API_KEY` in production

---

## Troubleshooting

### "Invalid activation token"
- Token expired (>48 hours)
- DB was reset (token no longer exists)
- Solution: Run `create-local` again, get new token

### "Tenant already activated"
- Tenant activation_status is 'active'
- Solution: Reset DB or change domain

### "Firebase tenant not found"
- Firebase tenant ID doesn't exist
- Solution: Run full `create` command first

### "OIDC provider not configured"
- Provider ID doesn't match Firebase
- Solution: Verify OIDC provider ID in Firebase Console

---

## Best Practices

1. **Save Firebase tenant IDs** from first setup
2. **Use `create-local`** for all testing iterations
3. **Reset DB often** to clear state
4. **Don't delete Firebase tenants** unless necessary
5. **Use different domains** for parallel testing
6. **Check console output** for activation URLs

---

## Command Comparison

| Feature | `create` | `create-local` |
|---------|----------|----------------|
| Creates Firebase tenant | ✅ Yes | ❌ No |
| Configures OIDC | ✅ Yes | ❌ No |
| Creates DB records | ✅ Yes | ✅ Yes |
| Sends activation email | ✅ Yes | ✅ Yes |
| Speed | ~5-10 seconds | ~2 seconds |
| Use case | Production, first setup | Testing, iterations |

---

## Quick Start for Testing

```bash
# 1. First time only - get Firebase tenant ID
docker-compose exec backend python -m cli.tenant_cli create \
  --company "MyCompany" --domain "mycompany.com" \
  --admin-email "admin@mycompany.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "xxx" --oidc-client-secret "yyy" \
  --oidc-issuer "https://mycompany.auth0.com"

# Save the Firebase Tenant ID from output (e.g., MyCompany-abc123)

# 2. Fast testing iterations
make reset-db
# When prompted:
#   Create tenant? y
#   Firebase Tenant ID: MyCompany-abc123
#   OIDC Provider ID: oidc.auth0
#   Company: TestIteration1
#   Domain: test.com
#   Admin Email: admin@test.com

# 3. Copy activation URL from console
# 4. Test activation flow in browser
# 5. Repeat from step 2 as needed
```

---

**Update:** 2025-11-23  
**For:** Quick testing and tenant onboarding workflow
