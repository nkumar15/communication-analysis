# Development & Testing Guide

Complete guide for developing and testing the Enterprise SSO tenant onboarding system.

---

## Quick Start for Developers

### Prerequisites
- Docker & Docker Compose
- Node.js 16+ (use nvm: `nvm use`)
- Python 3.11+
- Firebase Admin SDK credentials
- Auth0/Okta/Azure tenant (for OIDC)

### Initial Setup

```bash
# 1. Clone and setup
git clone <repo>
cd enterprisesso
make setup

# 2. Configure environment files
# Edit .env, backend/.env, frontend/.env
# Add Firebase credentials to secrets/firebase-credentials.json

# 3. Start services
make up

# 4. Run migrations
make migrate

# 5. Start frontend (new terminal)
cd frontend && npm start
```

**Access:**
- **B2B API**: http://localhost:8000/docs
- **Platform API**: http://localhost:8001/docs
- **B2C API**: http://localhost:8002/docs
- **Frontend**: http://localhost:3000

---

## Microservices Architecture

### Backend Services

The backend consists of 3 independent microservices:

| Service | Port | Purpose | Main Module |
|---------|------|---------|-------------|
| **B2B API** | 8000 | Enterprise tenant management | `services.b2b.main:app` |
| **Platform API** | 8001 | Platform administration | `services.platform.main:app` |
| **B2C API** | 8002 | Personal workspaces | `services.b2c.main:app` |

**Tech Stack:**
- FastAPI (Python async web framework)
- PostgreSQL with schema separation (`b2b`, `platform`, `b2c`, `farming`)
- SQLAlchemy ORM (async)
- Firebase Admin SDK (authentication, multi-tenancy)
- Resend (email service)

**Frontend:**
- React 18
- Firebase SDK (client-side auth)
- React Router

### Database Schemas

**b2b schema** - Enterprise tenants
- tenants, users, roles, invitations, role_permissions

**platform schema** - Platform admin
- platform_tenant, platform_users, platform_roles, platform_audit_log

**b2c schema** - Personal workspaces
- workspaces, b2c_users, workspace_members

**farming schema** - Domain logic
- farmers

For detailed architecture, see [System Architecture](../architecture/system-architecture.md)

---

## Database Management

### Migrations

**Run migrations:**
```bash
make migrate
# or
docker-compose exec b2b-api python migrations/run_migrations.py
```

**Create new migration:**
```bash
# Add SQL file to backend/migrations/
# Name format: 00X_description.sql
# Migrations run in alphabetical order
# All services share the same database/migrations
```

**Reset database (testing only):**
```bash
make reset-db
# Interactive: drops DB, runs migrations, optionally creates tenant
```

### Database Access

```bash
# PostgreSQL shell
make db-shell

# Quick queries
docker-compose exec -T postgres psql -U sso_user -d sso_db -c "SELECT * FROM tenants;"

# Check activation status
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "SELECT id, name, activation_status, activated_at FROM tenants;"
```

---

## Tenant Provisioning (CLI)

### Full Setup (First Time)

Creates Firebase tenant + OIDC + DB records:

```bash
docker-compose exec backend python -m cli.tenant_cli create \
  --company "Acme Corp" \
  --domain "acme.com" \
  --admin-email "admin@acme.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "your_client_id" \
  --oidc-client-secret "your_secret" \
  --oidc-issuer "https://acme.auth0.com"
```

**Output:** Firebase tenant ID, OIDC provider ID, activation URL

**Save the Firebase tenant ID for testing!**

### Quick Testing Mode

Reuses existing Firebase tenant (fast):

```bash
docker-compose exec backend python -m cli.tenant_cli create-local \
  --firebase-tenant-id "AcmeCorp-abc123" \
  --oidc-provider-id "oidc.auth0" \
  --company "Acme Test" \
  --domain "acme-test.com" \
  --admin-email "admin@acme-test.com"
```

**Use Case:** Repeated testing without creating Firebase tenants

### Interactive Workflow

```bash
# Reset DB and create tenant in one command
make reset-db

# Prompts for:
# - Create tenant? (y/n)
# - Firebase Tenant ID
# - OIDC Provider ID
# - Company, Domain, Email
```

---

## Testing & Verification

### 1. Platform Admin Testing (Super Admin)

Testing the isolated SaaS management system.

**Setup:**
```bash
# Seed platform tenant and create admin
make seed-system-tenant
make create-platform-admin
```

**Manual Verification:**
1. Go to `http://localhost:3000/platform-login`
2. Login with platform admin credentials
3. Verify access to Super Admin Dashboard

**Automated Tests:**
```bash
# Run platform integration tests
docker-compose exec backend python -m pytest tests/integration/test_platform_admin.py -v
```

### 2. Customer Tenant Testing (Standard Flow)

Testing the multi-tenant features (invitations, login, dashboard).

**Setup:**
```bash
# Create a test tenant
make tenant-create-local
```

**Manual Verification:**
1. Go to `http://localhost:3000/login`
2. Enter tenant user email (e.g., `admin@acme.com`)
3. Verify redirection to IdP and successful login

**Automated Tests:**
```bash
# Test Invitation Flow
make test-invitation

# Test Activation Flow
make test-activation
```

### 3. Security & Isolation Testing

Verify that tenants cannot access each other's data and regular users cannot access platform APIs.

```bash
# Run security isolation tests
make test-security
```

### 4. End-to-End Activation Test

**Complete flow:**

1. **Create tenant:**
   ```bash
   make reset-db  # Answer prompts
   # Copy activation URL from console
   ```

2. **Open activation link in browser:**
   ```
   http://localhost:3000/activate/TOKEN
   ```

3. **Complete activation:**
   - Click "Get Started"
   - SSO login popup opens
   - Login with OIDC provider
   - Click "Activate Account"
   - Redirected to dashboard ✅

4. **Verify database:**
   ```bash
   # Check tenant activated
   docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
     "SELECT name, activation_status FROM tenants;"
   
   # Check user created with admin role
   docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
     "SELECT email, role FROM users;"
   ```

### Testing Iteration Cycle

**Fast testing loop (60 seconds):**

```bash
# 1. Reset (10s)
make reset-db

# 2. Test activation (30s)
# Open URL → SSO login → Activate

# 3. Verify (5s)
# Check database state

# 4. Repeat!
```

### Error Scenario Testing

**Expired token:**
```bash
# Manually update token expiry
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "UPDATE tenants SET activation_expires_at = NOW() - INTERVAL '1 day';"
# Try activation → Should see "Token expired"
```

**Invalid token:**
```bash
# Use wrong token in URL
http://localhost:3000/activate/invalid-token-here
# Should see "Invalid activation token"
```

---

## API Endpoints

### Authentication

**Resolve Tenant**
```
POST /api/auth/resolve-tenant
Body: { "email": "user@company.com" }
Response: { "firebase_tenant_id": "...", "oidc_provider_id": "..." }
```

**Sync User** (After SSO login)
```
POST /api/auth/sync-user
Headers: Authorization: Bearer <firebase_token>
Response: { "user_id": 1, "email": "...", "role": "admin" }
```

### Activation

**Validate Token**
```
GET /api/activate/validate/{token}
Response: { "tenant_id": 1, "company": "...", "admin_email": "...", ... }
```

**Get Tenant Info**
```
GET /api/activate/tenant-info/{tenant_id}
Response: { "firebase_tenant_id": "...", "oidc_provider_id": "..." }
```

**Check Status**
```
GET /api/activate/check-status/{token}
Response: { "user_created": true, "user_id": 1 }
```

**Complete Activation**
```
POST /api/activate/complete
Headers: Authorization: Bearer <firebase_token>
Body: { "activation_token": "..." }
Response: { "message": "Tenant activated successfully", ... }
```

### Testing APIs

```bash
# Use FastAPI docs
open http://localhost:8000/docs

# Or curl
curl http://localhost:8000/api/activate/validate/TOKEN
```

---

## Development Commands

### Backend

```bash
# View logs
make logs

# Shell access
make shell

# Restart services
make restart

# Rebuild images
make build

# Stop services
make down

# Clean everything
make clean
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm start

# Build production
npm run build

# Check for errors
npm run lint
```

---

## Environment Variables

### Backend (.env, backend/.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://sso_user:sso_password@postgres:5432/sso_db

# Firebase
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/secrets/firebase-credentials.json

# Email (optional - falls back to console)
RESEND_API_KEY=re_xxx  # Get from resend.com

# App
FRONTEND_URL=http://localhost:3000
```

### Frontend (frontend/.env)

```env
# Firebase config (from Firebase Console)
REACT_APP_FIREBASE_API_KEY=xxx
REACT_APP_FIREBASE_AUTH_DOMAIN=xxx
REACT_APP_FIREBASE_PROJECT_ID=xxx
REACT_APP_FIREBASE_STORAGE_BUCKET=xxx
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=xxx
REACT_APP_FIREBASE_APP_ID=xxx

# Backend API
REACT_APP_API_URL=http://localhost:8000
```

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing Firebase credentials
# - Database connection failed
# - Port 8000 already in use

# Fix:
make down
make up
```

### Database errors

```bash
# Reset database
make reset-db

# Or manually:
docker-compose down -v  # WARNING: deletes all data
make up
make migrate
```

### Frontend shows CORS errors

- Check backend is running on port 8000
- Check `REACT_APP_API_URL` in frontend/.env
- Backend should allow CORS from localhost:3000

### SSO login fails

- Verify Firebase tenant ID is correct
- Check OIDC provider configured in Firebase Console
- Check OIDC client ID/secret are correct
- Allow popups in browser

### User created with wrong role

- Check invitation exists before SSO login
- Invitation should have role='admin'
- sync-user endpoint checks invitation

### Activation fails with "User not found"

- User must complete SSO login first
- Check user exists: `SELECT * FROM users;`
- Check firebase_uid matches

---

## Common Development Tasks

### Add a new migration

```bash
# 1. Create SQL file
touch backend/app/migrations/005_new_feature.sql

# 2. Write migration
# Use IF NOT EXISTS for idempotency

# 3. Run migration
make migrate
```

### Test email locally (without Resend)

```bash
# Don't set RESEND_API_KEY
# Emails will print to console
# Look for boxed output with activation URL
```

### Debug Firebase authentication

```bash
# Check token in backend logs
docker-compose logs backend | grep "verify_id_token"

# Check user sync
docker-compose logs backend | grep "sync-user"
```

### Clean up test data

```bash
# Quick reset
make reset-db

# Manual cleanup
docker-compose exec -T postgres psql -U sso_user -d sso_db -c \
  "TRUNCATE tenants, users, invitations RESTART IDENTITY CASCADE;"
```

---

## Production Checklist

Before deploying to production:

- [ ] Set strong database password
- [ ] Configure Resend API key
- [ ] Use production Firebase credentials
- [ ] Set FRONTEND_URL to production domain
- [ ] Enable HTTPS
- [ ] Configure Firebase authorized domains
- [ ] Set up database backups
- [ ] Configure logging/monitoring
- [ ] Verify OIDC redirect URIs
- [ ] Test with real OIDC providers

---

## Additional Resources

- [Testing Strategy](../testing/strategy.md) - Test plans & roadmap
- [Testing Workflows](../testing/workflows.md) - Detailed testing procedures
- [E2E Activation Guide](../testing/e2e-activation.md) - Step-by-step activation testing
- [API Docs](http://localhost:8000/docs) - Interactive API documentation
- [Firebase GCIP](https://cloud.google.com/identity-platform) - Multi-tenancy docs

---

**Last Updated:** 2025-11-23  
**Version:** 1.0
