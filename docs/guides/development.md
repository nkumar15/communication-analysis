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

# IMPORTANT: Set frontend API URLs in frontend/.env
REACT_APP_API_URL=http://localhost:8080

# 3. Start all services
make up          # Starts all backend APIs + frontend in Docker
# OR for local frontend development:
make dev         # Starts backend in Docker + frontend locally

# 4. Run migrations
make migrate
```

**Development Workflows:**

1. **Full Docker Stack** (`make up`):
   - All services run in Docker containers
   - Frontend: http://localhost:3000 (Dockerized)
   - Slower hot-reload for frontend changes

2. **Hybrid Development** (`make dev`) - **Recommended**:
   - Backend APIs run in Docker
   - Frontend runs locally with fast hot-reload
   - Best for frontend development

3. **Backend Only** (`make up-backend`):
   - Only starts backend services (no frontend container)
   - Use if you want to run frontend separately

**Access:**
- **Frontend**: http://localhost:3000
- **B2B API**: http://localhost:8000/docs
- **Platform API**: http://localhost:8001/docs
- **B2C API**: http://localhost:8002/docs

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
 
 ## Coding Standards & Best Practices
 
 ### 1. Transaction Management ("Flush vs Commit")
 
 **Rule**: Services `flush()`, Routers `commit()`.
 
 - **Services**:
   - Write business logic.
   - Use `await db.flush()` to generate IDs or check constraints.
   - **NEVER** call `await db.commit()`.
   - Leave the transaction open so routers can chain multiple services.
 
 - **Routers**:
   - Orchestrate services.
   - Call `await db.commit()` at the very end of the endpoint.
   - Handle exceptions and rollback if needed.
 
 ### 2. Writing Tests with RLS
 
 The system uses Row-Level Security (RLS). Your tests must set the tenant context or they will fail with `InsufficientPrivilegeError`.
 
 **Using `b2b_test_setup` (Recommended):**
 This fixture provides a pre-configured `TenantAwareSession` that handles RLS automatically.
 
 ```python
 async def test_example(api_client, b2b_test_setup):
     setup = b2b_test_setup
     session = setup['session']  # TenantAwareSession
     
     # This automatically executes SET LOCAL app.current_tenant_id...
     result = await session.execute(select(User))
 ```
 
 **Using Raw Session (e.g., Domain tests):**
 If you use a raw `db_session`, you **MUST** manually set the context before querying RLS-protected tables.
 
 ```python
 from sqlalchemy import text
 
 async def test_manual_context(db_session, tenant):
     # Set context
     await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant.id}'"))
     
     # Now you can query
     await db_session.execute(select(Project)...)
 ```
 
 ---

## Platform Administration (CLI)

### Setup Platform Tenant

Interactive wizard for creating the platform admin system:

```bash
make platform-seed
```

**Prompts for:**
- Firebase Tenant ID (default: `platform-system`)
- OIDC Provider ID (default: `platform-oidc`)
- Platform Name (default: `SaaS Platform`)
- Email Domain (default: `platform.local`)

**Creates:**
- Platform tenant record
- Platform roles (Platform Administrator, Support Staff, Billing Manager)

### Create Platform Admin User

Interactive wizard for creating platform administrators:

```bash
make platform-create-admin
```

**Prompts for:**
- Email (must use configured Firebase tenant)
- Display Name (optional)

**Creates:**
- Firebase user in platform tenant
- Platform admin record in database

**Access:** http://localhost:3000/platform-login

---

## B2B Tenant Provisioning (CLI)

### Create Customer Tenant (Interactive)

Interactive wizard for creating B2B customer tenants:

```bash
make b2b-seed
```

**Prompts for:**
- Firebase Tenant ID (existing tenant from GCIP)
- OIDC Provider ID (configured in Firebase)
- Company Name
- Domain (e.g., `acme.com`)
- Admin Email

**Creates:**
- Tenant record in database
- RBAC roles (admin, field_manager, field_agent)
- Admin invitation email
- Activation token (48-hour expiry)

**Activation Flow:**
1. Admin receives email with activation link
2. Admin visits link: http://localhost:3000/activate/{token}
3. Admin logs in via SSO
4. Account activated

### Alternative: Full Automation

For production use, create tenant with full Firebase automation:

```bash
docker-compose exec b2b-api python /app/scripts/b2b/tenant_onboard.py create \
  --company "Acme Corp" \
  --domain "acme.com" \
  --admin-email "admin@acme.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "your_client_id" \
  --oidc-client-secret "your_secret" \
  --oidc-issuer "https://acme.auth0.com"
```

**Note:** This creates both the Firebase tenant AND the database record.
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

### 4. E2E Browser Testing (Playwright)

Run full end-to-end tests using a headless browser against the Dockerized stack.

```bash
# Run all browser tests
make test-browser
```

**Note on Caching:** The build uses a unified multi-stage Dockerfile. The `test` stage caches system and python dependencies (including Playwright browsers), so subsequent runs are very fast.

### 5. Domain API Testing (Projects, Tasks, Comments)

Test the core domain features with multi-tenant isolation and RBAC enforcement.

**Run all domain tests:**
```bash
# All domain API tests (31 tests)
docker-compose run --rm e2e-tests pytest tests/e2e_api/domain/ -v

# Individual test files
docker-compose run --rm e2e-tests pytest tests/e2e_api/domain/test_projects.py -v
docker-compose run --rm e2e-tests pytest tests/e2e_api/domain/test_tasks.py -v
docker-compose run --rm e2e-tests pytest tests/e2e_api/domain/test_comments.py -v
```

**Test coverage includes:**
- ✅ CRUD operations for Projects, Tasks, Comments
- ✅ Multi-tenant isolation (tenants cannot see each other's data)
- ✅ Team-based scoping (members only see their team's projects)
- ✅ RBAC permissions (owner, admin, team_member roles)
- ✅ Task assignment validation
- ✅ Threaded comment structure

**Manual API testing:**
```bash
# 1. Seed domain data (creates resources for permission checks)
docker-compose exec b2b-api python scripts/b2b/seed_domain_data.py

# 2. Create a tenant with teams
make reset-db

# 3. Test via Swagger UI
open http://localhost:8000/docs

# 4. Create project, tasks, and comments via UI
# Verify multi-tenant isolation by creating a second tenant
```

**Key test scenarios:**
- Create project in team → Only team members can see it
- Create task → Only assignable to team members
- Add threaded comments → Replies nest correctly
- Cross-tenant access → Returns 403 Forbidden

See [Domain APIs Architecture](../architecture/domain-apis.md) for complete API documentation.

### 6. End-to-End Activation Test

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

# Backend API URLs (IMPORTANT: Must use localhost, not Docker hostnames)
REACT_APP_API_URL=http://localhost:8080 # API Gateway
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
# - Port 8000 already in use (check for old containers)

# Fix:
make down
# If port still in use:
docker-compose down -v
# Check for zombie containers:
docker ps
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
---

## Structured Logging

The application uses `structlog` for cloud-adaptive structured logging across all microservices.

### Configuration

Logging behavior is controlled by environment variables in `.env`:

```bash
LOG_ENVIRONMENT=local    # local, gcp, aws, production
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_JSON_INDENT=2       # Pretty print JSON (local only)

# For cloud deployments
GCP_PROJECT_ID=your-project-id
AWS_REGION=us-east-1
```

### Log Formats

**Local Development** (`LOG_ENVIRONMENT=local`):
- Human-readable colored console output
- Key-value pairs for easy scanning
- Example:
  ```
  2025-12-01T07:11:42Z [info] b2b_api_ready
    database=connected
    firebase=initialized
    service=b2b-api
  ```

**GCP** (`LOG_ENVIRONMENT=gcp`):
- JSON format with GCP Cloud Logging fields
- Includes `severity`, `timestamp`, `logging.googleapis.com/trace`
- Compatible with Cloud Logging ingestion

**AWS** (`LOG_ENVIRONMENT=aws`):
- JSON format for CloudWatch Logs
- Includes `level`, `timestamp` (Unix ms), `aws_request_id`
- Compatible with CloudWatch ingestion

### Request Tracing

All HTTP requests automatically get:
- **`request_id`**: Unique UUID for each request
- **HTTP metadata**: method, path, client IP, user-agent
- **User context**: tenant_id, user_id (from JWT when available)
- **Duration tracking**: Request completion time in milliseconds

**Example log chain for a single request:**
```
[info] request_started request_id=abc-123 http_method=POST
[info] tenant_resolution_started request_id=abc-123 email=user@company.com
[warning] tenant_not_found request_id=abc-123 domain=company.com
[info] request_completed request_id=abc-123 duration_ms=45 status_code=404
```

All logs with the same `request_id` belong to the same request, enabling distributed tracing.

### Usage in Code

```python
from core.logging import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("user_created", user_id="123", email="user@example.com")

# Warning with context
logger.warning("payment_failed", 
               user_id="123",
               amount=99.99,
               reason="insufficient_funds")

# Error with exception
try:
    risky_operation()
except Exception as e:
    logger.error("operation_failed",
                 operation="risky_operation",
                 exc_info=True)  # Includes stack trace
```

**Context is automatically added** via middleware:
- `request_id` - unique per request
- `tenant_id` - from JWT token
- `user_id` - from JWT token
- `http_method`, `http_path` - HTTP metadata
- `client_ip` - request origin

### Viewing Logs

**All services:**
```bash
make logs              # All containers
make logs-b2b          # B2B API only
make logs-platform     # Platform API only
make logs-b2c          # B2C API only
make logs-domain       # Domain API only
```

**Filter by request ID:**
```bash
docker-compose logs b2b-api | grep "request_id=abc-123"
```

**Follow logs in real-time:**
```bash
make logs-b2b ARGS="-f"
```

### Production Deployment

1. **Set environment for cloud provider:**
   ```bash
   LOG_ENVIRONMENT=gcp
   GCP_PROJECT_ID=my-project
   ```

2. **Logs automatically output JSON** compatible with cloud logging services

3. **Configure log aggregation:**
   - GCP: Logs auto-collected by Cloud Logging
   - AWS: Configure CloudWatch Logs agent
   - Other: Use Fluentd/Logstash to forward to your log aggregator

### Utilities

**PII Sanitization:**
```python
from core.logging.utils import mask_email, sanitize_pii

# Mask email
masked = mask_email("user@example.com")  # "u***@example.com"

# Sanitize dictionary (masks common PII fields)
data = sanitize_pii({"email": "user@example.com", "ssn": "123-45-6789"})
```

---

## Debugging & Troubleshooting

### View Logs

**All Backend APIs:**
```bash
make logs              # View all backend API logs (B2B, Platform, B2C)
```

**Individual Services:**
```bash
make logs-b2b          # B2B API only
make logs-platform     # Platform API only
make logs-b2c          # B2C API only
make logs-all          # All services including frontend
```

### Access Container Shell

```bash
make shell-b2b         # B2B API container
make shell-platform    # Platform API container
make shell-b2c         # B2C API container
```

### Debug Firebase authentication

```bash
# Check user sync
make logs-b2b | grep "sync-user"
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

**Last Updated:** 2025-11-30  
**Version:** 1.1

---

## 🕒 Timezone Handling

The application is designed to be timezone-agnostic in the backend and timezone-aware in the frontend.

### Backend (UTC Only)
- **Rule:** ALWAYS store and manipulate dates in **UTC**.
- **Utility:** Use `core.utils.get_utc_now()` instead of `datetime.utcnow()`.
- **Reason:** `datetime.utcnow()` returns a "naive" datetime (no timezone info), which can cause ambiguity. `get_utc_now()` returns a timezone-aware UTC datetime.

```python
from core.utils import get_utc_now

# Correct
created_at = get_utc_now()

# Incorrect
created_at = datetime.utcnow()
```

### Frontend (Local Time)
- **Rule:** Display dates in the user's **local timezone**.
- **Utility:** Use `src/utils/dateUtils.js`.

```javascript
import { formatDateTime } from '../utils/dateUtils';

// Displays: "Oct 27, 2023, 10:00 AM" (in user's local time)
<span>{formatDateTime(tenant.created_at)}</span>
```

---

## 🗑️ Soft Delete

We use a "Soft Delete" mechanism for critical entities (`Tenant`, `User`, `AuthProvider`) to preserve data for audit and recovery.

### Implementation
- **Mixin:** `core.models.base.SoftDeleteMixin` adds:
    - `deleted_at` (Timestamp, nullable)
    - `is_deleted` (Property)
- **Database:** Rows remain in the table but `deleted_at` is set.
- **Filtering:** Services automatically filter out soft-deleted records.

### Usage

**In Models:**
```python
from core.models.base import SoftDeleteMixin

class TenantModel(Base, TimestampMixin, SoftDeleteMixin):
    ...
```

**In Services:**
```python
# Delete (Soft)
await tenant_service.delete_tenant(db, tenant_id)

# Query (Automatically filters deleted)
# The service methods include .where(Model.deleted_at.is_(None))
tenant = await tenant_service.get_tenant_by_id(db, tenant_id)
```

