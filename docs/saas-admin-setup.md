# SaaS Admin Console - Manual Testing Guide

## Prerequisites
- Docker containers running (`docker-compose up -d`)
- Backend and Frontend services active

## Step 1: Seed System Tenant & Platform Admin Role

Run the seeding script to create the System Tenant:

```bash
cd /home/neeraj/codes/enterprisesso
docker-compose exec backend python scripts/seed_system_tenant.py
```

**Expected Output:**
```
🌱 Seeding SaaS Admin Foundation...
Creating System Tenant...
✅ System Tenant created: <uuid>
Creating Platform Admin Role...
✅ Platform Admin Role created
✨ Seeding complete!
```

## Step 2: Create a Platform Admin User

You need to manually create a user with the `platform_admin` role. Use the database directly:

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U sso_user -d sso_db
```

**SQL Commands:**

```sql
-- 1. Find the System Tenant ID
SELECT id, name FROM tenants WHERE firebase_tenant_id = 'system-platform';
-- Copy the UUID from this query

-- 2. Find the platform_admin role ID
SELECT id, name FROM roles WHERE name = 'platform_admin';
-- Copy the UUID from this query

-- 3. Create platform admin user
-- Replace <SYSTEM_TENANT_ID> and <PLATFORM_ADMIN_ROLE_ID> with actual UUIDs
INSERT INTO users (tenant_id, email, firebase_uid, name, role_id, is_active)
VALUES (
    '<SYSTEM_TENANT_ID>',
    'superadmin@platform.local',
    'platform-admin-001',  -- Temporary UID for testing
    'Platform Super Admin',
    '<PLATFORM_ADMIN_ROLE_ID>',
    true
);
```

**Exit PostgreSQL:**
```sql
\q
```

## Step 3: Create Some Test Tenants

Use the API to create test tenants (requires platform admin authentication):

```bash
# First, get a temporary auth token for your platform admin
# (In production, use Firebase; for testing, you can insert directly)

# Option: Create test tenants via SQL
docker-compose exec postgres psql -U sso_user -d sso_db
```

```sql
-- Create test tenant 1
INSERT INTO tenants (name, domain, firebase_tenant_id, oidc_provider_id, activation_status, is_active)
VALUES 
    ('Acme Corporation', 'acme.com', 'tenant-acme', 'oidc-acme', 'active', true),
    ('Widget Inc', 'widget.io', 'tenant-widget', 'oidc-widget', 'active', true),
    ('TechStart LLC', 'techstart.co', 'tenant-techstart', 'oidc-techstart', 'pending', true);

-- Get tenant IDs for creating users
SELECT id, name, domain FROM tenants WHERE firebase_tenant_id LIKE 'tenant-%';

-- Create admin role for Acme (example, repeat for others)
-- First, get the tenant ID for 'Acme Corporation'
INSERT INTO roles (tenant_id, name, display_name, is_system_role)
SELECT id, 'admin', 'Admin', true FROM tenants WHERE domain = 'acme.com';

-- Create some users for Acme
INSERT INTO users (tenant_id, email, firebase_uid, name, role_id, is_active)
SELECT t.id, 'admin@acme.com', 'firebase-acme-admin', 'Acme Admin', r.id, true
FROM tenants t
JOIN roles r ON r.tenant_id = t.id AND r.name = 'admin'
WHERE t.domain = 'acme.com';

-- Add more users to different tenants for stats
INSERT INTO users (tenant_id, email, firebase_uid, name, role_id, is_active)
SELECT t.id, 'user1@widget.io', 'firebase-widget-1', 'Widget User 1', r.id, true
FROM tenants t
JOIN roles r ON r.tenant_id = t.id
WHERE t.domain = 'widget.io' LIMIT 1;

\q
```

## Step 4: Access the SaaS Admin Console

### Option A: Using the UI (Requires Firebase Setup)

1. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

2. **Navigate to:** `http://localhost:3000/super-admin`

3. **Login:** Use Firebase authentication with the platform admin user

### Option B: Direct API Testing (No Firebase Required)

Test the platform API endpoints directly:

```bash
# Get platform stats
curl -X GET http://localhost:8000/api/platform/stats \
  -H "Authorization: Bearer <your-mock-token>"

# List all tenants
curl -X GET http://localhost:8000/api/platform/tenants \
  -H "Authorization: Bearer <your-mock-token>"

# Create a new tenant
curl -X POST http://localhost:8000/api/platform/tenants \
  -H "Authorization: Bearer <your-mock-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Test Tenant",
    "domain": "newtest.com",
    "admin_email": "admin@newtest.com",
    "plan": "free"
  }'
```

## Step 5: Test Impersonation Feature

Once you have test tenants with admin users:

```bash
# Get a tenant ID
docker-compose exec postgres psql -U sso_user -d sso_db -c \
  "SELECT id FROM tenants WHERE domain = 'acme.com';"

# Impersonate (via API)
curl -X POST http://localhost:8000/api/platform/tenants/<TENANT_ID>/impersonate \
  -H "Authorization: Bearer <platform-admin-token>"
```

This returns an impersonation token you can use to access the tenant's dashboard.

## Quick Verification Checklist

- [ ] System Tenant created
- [ ] Platform Admin role created
- [ ] Platform Admin user exists
- [ ] 2-3 test tenants created
- [ ] Test tenant users created
- [ ] Can access `/super-admin` route
- [ ] Can see tenant list with stats
- [ ] Can create new tenant via UI
- [ ] Can click "Login As" button
- [ ] Impersonation banner appears

## Troubleshooting

**401 Unauthorized on /api/platform endpoints:**
- Ensure your user has `platform_admin` role
- Check Firebase token is valid
- Verify middleware is loading correctly

**404 on /super-admin route:**
- Ensure frontend is running
- Check React Router routes in `App.js`

**Empty tenant list:**
- Run the SQL commands above to create test tenants
- Check database connection

**"Login As" returns 404:**
- Ensure target tenant has at least one admin user
- Check role exists for that tenant

---

**Database Schema Reference:**

```sql
-- Useful queries for debugging
SELECT * FROM tenants;
SELECT * FROM users;
SELECT * FROM roles;

-- Check platform admin setup
SELECT u.*, r.name as role_name, t.name as tenant_name
FROM users u
JOIN roles r ON u.role_id = r.id
JOIN tenants t ON u.tenant_id = t.id
WHERE r.name = 'platform_admin';
```
