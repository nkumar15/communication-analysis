# Platform Admin Setup Guide

## Overview

The platform admin system provides a **completely isolated administration layer** for managing your SaaS platform. Platform admins have their own:
- Dedicated database tables (`platform_tenant`, `platform_users`, `platform_roles`, `platform_audit_log`)
- Separate Firebase tenant for authentication
- Isolated API endpoints (`/api/platform/*`)
- Dedicated login page and dashboard

This ensures complete separation from customer tenant systems for security and clarity.

---

## Architecture

### Database Tables

| Table | Purpose |
|-------|---------|
| `platform_tenant` | Singleton representing your platform |
| `platform_roles` | Platform-specific roles (admin, support, billing) |
| `platform_users` | Platform administrators and staff |
| `platform_audit_log` | Audit trail for all platform actions |

### Separation from Customer System

| Aspect | Customer Tenants | Platform System |
|--------|-----------------|-----------------|
| Database Tables | `tenants`, `users`, `roles` | `platform_tenant`, `platform_users`, `platform_roles` |
| Firebase Tenant | Per-customer tenants | Single platform tenant |
| Login URL | `/login` | `/platform-login` |
| Auth Endpoint | `/api/auth/me` | `/api/platform/auth/me` |
| Dashboard | `/dashboard` | `/super-admin` |

---

## Setup Instructions

### Prerequisites

1. Docker and Docker Compose installed
2. Firebase project with GCIP (Google Cloud Identity Platform) enabled
3. Services running: `make up`

### Step 1: Run Database Migration

The migration creates all platform tables.

```bash
make migrate
```

**Expected Output:**
```
⏭️  Skipping (already applied): 001_schema.sql
...
🔄 Running migration: 008_separate_platform_system.sql
✅ Completed: 008_separate_platform_system.sql
```

**Verify tables created:**
```bash
make db-shell
# Inside PostgreSQL shell:
\dt platform_*
```

You should see: `platform_tenant`, `platform_roles`, `platform_users`, `platform_audit_log`

### Step 2: Configure Firebase Platform Tenant

1. **Create Platform Tenant in Firebase GCIP:**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Navigate to Authentication → Settings → Tenants
   - Click "Add Tenant"
   - Name: "Platform System" (or your company name)
   - Note the **Tenant ID** (e.g., `platform-abc123`)

2. **Configure OIDC Provider:**
   - In your new platform tenant, go to "Sign-in methods"
   - Enable "SAML" or your preferred OIDC provider
   - Configure your identity provider (Okta, Azure AD, Google, etc.)
   - Note the **Provider ID** (e.g., `oidc.okta`)

### Step 3: Seed Platform Foundation

Interactive wizard to create the platform tenant record and default roles:

```bash
make platform-seed
```

**Prompts:**
- **Firebase Tenant ID**: Enter the tenant ID from GCIP (e.g., `platform-abc123`)
- **OIDC Provider ID**: Enter your configured provider ID (e.g., `oidc.okta`)
- **Platform Name**: Your platform name (default: `SaaS Platform`)
- **Email Domain**: Your company email domain (default: `platform.local`)

**Expected Output:**
```
✨ Creating Platform Tenant...
   ✅ Platform Tenant created: My SaaS Platform

📋 Creating Platform Roles...
   ✅ Created role: Platform Administrator
   ✅ Created role: Support Staff
   ✅ Created role: Billing Manager

✅ Platform foundation setup complete!
```

**Verify in database:**
```bash
docker compose exec -T postgres psql -U sso_user -d sso_db -c "SELECT name, firebase_tenant_id FROM platform_tenant"
docker compose exec -T postgres psql -U sso_user -d sso_db -c "SELECT name, display_name FROM platform_roles"
```

### Step 4: Create Platform Admin User

   Firebase Tenant ID: platform-abc123

✅ Found platform role: Platform Administrator

🔥 Creating Firebase user in platform tenant...
   ✅ Created Firebase user: AbC123XyZ...

💾 Creating platform user in database...
✅ Platform user created successfully!

📋 User Details:
   ID: cc516421-dd8e-4a6a-90aa-56f5738392a0
   Email: admin@mycompany.com
   Name: John Doe
   Role: Platform Administrator
   Firebase UID: AbC123XyZ...

🔐 Login Instructions:
   1. Go to: http://localhost:3000/platform-login
   2. Login with: admin@mycompany.com
   3. Use your OIDC provider configured in Firebase
```

**Verify in database:**
```bash
docker compose exec -T postgres psql -U sso_user -d sso_db -c "SELECT email, display_name, is_active FROM platform_users"
```

**Alternative (non-interactive):**

If you prefer to run the command directly without interactive prompts:

```bash
docker compose exec backend python scripts/create_platform_admin.py \
  --email admin@mycompany.com \
  --name "John Doe"
```

### Step 5: Test Platform Login

1. Navigate to `http://localhost:3000/platform-login`
2. Click "Login as Platform Admin"
3. Sign in using your OIDC provider
4. You should be redirected to `/super-admin`

---

## Platform Login Flow

### How Dynamic Configuration Works

The platform login page automatically discovers the Firebase configuration:

1. **Frontend loads** `/platform-login`
2. **Fetches config** from `GET /api/platform/config` (public endpoint)
3. **Receives:**
   ```json
   {
     "firebase_tenant_id": "platform-abc123",
     "oidc_provider_id": "oidc.okta",
     "tenant_name": "My SaaS Platform"
   }
   ```
4. **Initializes Firebase** with this tenant ID
5. **User clicks login** → OIDC flow begins
6. **After authentication** → validates with `/api/platform/auth/me`
7. **Redirects** to `/super-admin`

### Authentication vs Customer Tenants

| Step | Customer Tenant Flow | Platform Admin Flow |
|------|---------------------|---------------------|
| 1. Login page | `/login` | `/platform-login` |
| 2. Tenant discovery | Email domain lookup | API config endpoint |
| 3. Firebase tenant | Customer's tenant | Platform tenant |
| 4. After auth | Creates/updates in `users` | Validates from `platform_users` |
| 5. Auth endpoint | `/api/auth/me` | `/api/platform/auth/me` |
| 6. Dashboard | `/dashboard` | `/super-admin` |

**Key difference:** Platform admins are **pre-created** in the database. Customer users are **auto-created** on first login.

---

## API Endpoints

### Public Endpoints

**Get Platform Config**
```bash
GET /api/platform/config
```
Returns Firebase configuration for platform login. No authentication required.

### Protected Endpoints (Require Platform Admin Auth)

**Get Platform Admin Info**
```bash
GET /api/platform/auth/me
Authorization: Bearer <firebase_jwt>
```

**Get Platform Statistics**
```bash
GET /api/platform/stats
```

**List Customer Tenants**
```bash
GET /api/platform/tenants?skip=0&limit=20&search=acme
```

**Create Customer Tenant**
```bash
POST /api/platform/tenants
{
  "name": "Acme Corp",
  "domain": "acme.com",
  "admin_email": "admin@acme.com"
}
```

**Impersonate Tenant Admin**
```bash
POST /api/platform/tenants/{tenant_id}/impersonate
```

---

## Administration Tasks

### Adding More Platform Admins

```bash
make create-platform-admin
# Enter email and name when prompted
```

### Adding Support Staff or Billing Managers

```bash
docker compose exec backend python scripts/create_platform_admin.py \
  --email support@mycompany.com \
  --name "Jane Support" \
  --role support_staff
```

Available roles:
- `platform_admin` - Full platform access
- `support_staff` - Customer support access
- `billing_manager` - Billing and payments access

### Viewing Platform Audit Logs

```bash
docker compose exec -T postgres psql -U sso_user -d sso_db -c \
  "SELECT created_at, user_email, action, resource_type, details 
   FROM platform_audit_log 
   ORDER BY created_at DESC 
   LIMIT 10"
```

---

## Troubleshooting

### "Platform configuration not found" Error

**Symptoms:** `/api/platform/config` returns 404

**Solution:**
```bash
# Check if platform tenant exists
make db-shell
SELECT * FROM platform_tenant;

# If empty, run seeding
make seed-system-tenant
```

### 401 Unauthorized on Platform APIs

**Symptoms:** Can't access `/api/platform/stats` or other protected endpoints

**Possible causes:**

1. **User not in platform_users table:**
   ```bash
   # Create the user
   make create-platform-admin
   ```

2. **Wrong Firebase tenant:**
   - Ensure you're logging in via `/platform-login` (not `/login`)
   - Check browser developer tools → Network tab
   - Verify JWT contains correct tenant ID

3. **User is inactive:**
   ```sql
   UPDATE platform_users SET is_active = true WHERE email = 'your@email.com';
   ```

### Firebase User Already Exists Error

**Symptoms:** Script fails with "Firebase user already exists"

**Solution:** This is usually fine. The script will use the existing Firebase user and just create the database record.

If you need to recreate:
```bash
# Delete from Firebase Console first
# Then run script again
make create-platform-admin
```

### Can't Access /super-admin Page

**Checklist:**
1. ✅ Platform user created in database
2. ✅ Logged in via `/platform-login` (not `/login`)
3. ✅ JWT token stored in browser (check Local Storage)
4. ✅ Frontend route protection configured for `/super-admin`

### Database Table Not Found

**Symptoms:** `ERROR: relation "platform_tenant" does not exist`

**Solution:**
```bash
# Ensure migration ran
make migrate

# Verify tables exist
make db-shell
\dt platform_*
```

---

## Testing

### Manual Testing

1. **Test config endpoint:**
   ```bash
   curl http://localhost:8001/api/platform/config
   ```
   Should return Firebase tenant configuration.

2. **Test authentication:**
   - Login via `/platform-login`
   - Open browser DevTools → Application → Local Storage
   - Should see Firebase auth token

3. **Test protected endpoint (should fail without auth):**
   ```bash
   curl http://localhost:8001/api/platform/stats
   # Should return 401 Unauthorized
   ```

### Automated Tests

Run the full platform test suite:

```bash
make e2e-test
```

This runs:
- Platform authentication tests
- Platform authorization tests  
- Multi-tenant isolation tests
- Platform security tests

**Expected:** All tests should pass.

---

## Security Considerations

### Best Practices

1. **Use strong authentication:**
   - Enable MFA for all platform admin accounts
   - Use enterprise OIDC provider (Okta, Azure AD, Google Workspace)

2. **Limit platform admin accounts:**
   - Only create accounts for employees who need platform access
   - Use `support_staff` or `billing_manager` roles for limited access

3. **Monitor audit logs:**
   - Regularly review `platform_audit_log` table
   - Set up alerts for sensitive actions (tenant creation, impersonation)

4. **Separate Firebase tenants:**
   - Never use the same Firebase tenant for platform and customers
   - This ensures complete authentication isolation

5. **Protect Firebase credentials:**
   - Store `firebase-credentials.json` securely
   - Never commit to version control
   - Rotate credentials periodically

### Audit Logging

All platform admin actions are automatically logged to `platform_audit_log` including:
- User email
- Action performed
- Resource affected
- IP address
- Timestamp
- Additional details (JSON)

---

## Commands Quick Reference

For a complete list of commands and detailed testing workflows, see the [Development Guide](development.md).

| Command | Purpose |
|---------|---------|
| `make migrate` | Run database migrations |
| `make seed-system-tenant` | Create platform tenant and roles |
| `make create-platform-admin` | Create platform administrator |
| `make db-shell` | Open PostgreSQL shell |
| `make e2e-test` | Run platform integration tests |
| `make up` | Start all Docker services |
| `make down` | Stop all Docker services |
| `make logs` | View backend logs |
