# System Architecture Overview

## Microservices Architecture

The system is designed as a **microservices architecture** with 3 independent backend services sharing a common database.

### Service Topology

```
┌─────────────┐
│   Frontend  │  React App (Port 3000)
│   (React)   │
└──────┬──────┘
       │
       ├────────────┬────────────┬─────────────┐
       │            │            │             │
┌──────▼──────┐┌───▼────────┐┌──▼──────────┐
│  B2B API    ││Platform API││  B2C API    │
│  Port 8000  ││  Port 8001 ││  Port 8002  │
└──────┬──────┘└────┬───────┘└──┬──────────┘
       │            │            │
       └────────────┴────────────┴─────────────┐
                                               │
                                        ┌──────▼──────┐
                                        │  PostgreSQL │
                                        │  (Shared)   │
                                        └─────────────┘
```

---

## Backend Services

### 1. B2B API (Port 8000)
**Purpose:** Enterprise tenant management

**Responsibilities:**
- Tenant activation and onboarding
- User authentication
- Invitation management
- Role-based access control (RBAC)
- Domain-specific features (farming, etc.)

**Routers:**
- `/api/auth` - Authentication endpoints
- `/api/activation` - Tenant activation
- `/api/invitations` - User invitation flow
- `/api/users` - User management
- `/api/roles` - RBAC configuration
- `/api/farmers` - Domain-specific (example)

---

### 2. Platform API (Port 8001)
**Purpose:** SaaS platform administration

**Responsibilities:**
- Platform admin authentication
- Tenant creation and management
- Tenant impersonation
- Platform-wide analytics and stats

**Routers:**
- `/api/platform/stats` - Global statistics
- `/api/platform/tenants` - Tenant CRUD
- `/api/platform/tenants/{id}/impersonate` - Admin impersonation

**Security:** Should run on internal network in production

---

### 3. B2C API (Port 8002)
**Purpose:** Personal and team workspace management

**Status:** Skeleton implementation

**Planned Features:**
- Workspace creation (personal/team)
- User profiles
- Workspace member management
- Subscription/billing integration

---

## Database Architecture

### Schema Separation

PostgreSQL database with 4 logical schemas:

| Schema | Purpose | Tables |
|--------|---------|--------|
| **b2b** | Enterprise tenants | tenants, users, roles, invitations, role_permissions |
| **platform** | Platform admin | platform_tenant, platform_users, platform_roles, platform_audit_log |
| **b2c** | Personal workspaces | workspaces, b2c_users, workspace_members |
| **farming** | Domain logic | farmers |

### Multi-Tenancy Model
 
 **Row-Level Security (RLS):**
 - **Enforcement**: PostgreSQL RLS policies scoped by `tenant_id`.
 - **Context Setting**: Middleware (`b2b_auth.py`) executes `SET LOCAL app.current_tenant_id` for every request.
 - **Safety**: If context is not set, queries fail (blocking accidental data leakage).
 
 **Schema Isolation:**
 - **Platform**: `platform` schema (super-admin only).
 - **B2B**: `b2b` schema (multi-tenant, shared tables).
 - **B2C**: `b2c` schema (user-centric).
 - **Domains**: `farming`, `domain` schemas (business logic).
 
 ---
 
 ## Transaction & Data Integrity
 
 ### "Service Flush, Router Commit" Pattern
 To ensure atomicity and standardization, the backend follows a strict transaction boundary pattern:
 
 1.  **Services (Business Logic)**:
     - **NEVER** call `commit()`.
     - `add()`, `update()`, or `delete()` objects.
     - Call `await db.flush()` if ID generation or constraints are needed immediately.
     - Return the object attached to the active session.
 
 2.  **Routers (API Layer)**:
     - Receive the object from Service.
     - Responsible for the final `await db.commit()`.
     - Or rely on `FastAPI` dependency injection to commit on success (if configured).
 
 **Why?**
 - Allows composing multiple service calls into a single atomic transaction.
 - Prevents partial data writes if a later step fails.
 - Simplifies testing by allowing easy rollbacks.
 
 ---

## Frontend Architecture

### Module Structure

```
frontend/src/modules/
├── b2b/           # Enterprise tenant UI
│   ├── auth/
│   ├── dashboard/
│   └── users/
├── platform/      # Platform admin console
│   ├── tenants/
│   └── stats/
└── b2c/           # Personal workspace UI
    ├── dashboard/
    └── settings/
```

### Routing

- B2B: `/`, `/dashboard`, `/users`, `/invite`
- Platform: `/platform/*`
- B2C: `/workspace/*`

---

## Authentication Flow

### Firebase GCIP Multi-Tenancy

```
1. User visits login page
2. Frontend queries tenant by domain
3. Frontend initializes Firebase with tenant_id
4. User redirected to OIDC provider (Auth0, Okta, etc.)
5. OIDC completes, Firebase issues JWT
6. Frontend sends JWT to backend
7. Backend validates with Firebase Admin SDK
8. Backend returns user data + role
```

### Token Flow

```
Frontend                    Backend                 Firebase
   │                          │                        │
   ├─── JWT in Header ───────>│                        │
   │                          ├─── Verify Token ─────>│
   │                          │<──── User Claims ──────┤
   │                          │                        │
   │<─── User + Role ─────────┤                        │
```

---

## Deployment Architecture

### Development (docker-compose)
```yaml
services:
  b2b-api:      # target: b2b
  platform-api: # target: platform
  b2c-api:      # target: b2c
  postgres:     # Port 5432
  frontend:     # Port 3000
  e2e-tests:    # target: test
```

### Production (Recommended)
```
┌─────────────────────────────────────┐
│         Load Balancer / NGINX        │
└─────────────┬───────────────────────┘
              │
      ┌───────┴───────┬───────────────┐
      │               │               │
┌─────▼────┐    ┌─────▼────┐    ┌────▼─────┐
│ B2B API  │    │Platform  │    │ B2C API  │
│Container │    │Container │    │Container │
└─────┬────┘    └─────┬────┘    └────┬─────┘
      │               │               │
      └───────────────┴───────────────┘
                      │
              ┌───────▼────────┐
              │   PostgreSQL   │
              │   (RDS/Cloud)  │
              └────────────────┘
```

---

## Key Architectural Decisions

### Why Microservices?

**✅ Benefits:**
- **Independent Deployment** - Deploy B2B without affecting Platform
- **Scalability** - Scale each service based on load
- **Clear Boundaries** - Explicit service responsibilities
- **Security** - Platform API can be internal-only
- **Team Autonomy** - Different teams own different services

**⚠️ Trade-offs:**
- Shared database (not fully decoupled)
- Transactions across services limited
- More complex deployment

### Why Shared Database?

**✅ Benefits:**
- **ACID Transactions** - Cross-service data consistency
- **Simplified Queries** - JOIN across schemas
- **Single Migration System** - Easier schema evolution
- **Cost Effective** - One database instance

**⚠️ Trade-offs:**
- Services coupled at data layer
- Schema changes require coordination
- Cannot scale database per-service

**Future:** May split to separate databases if needed for scale

---

## Security Architecture

### Authentication
- **Stateless JWT** - Firebase-issued tokens
- **No Sessions** - Fully stateless backend
- **Token Validation** - Firebase Admin SDK verifies all requests

### Authorization
- **RBAC** - role_permissions table maps roles to actions
- **RLS** - PostgreSQL enforces tenant_id isolation
- **Platform Isolation** - Separate platform schema and auth

### Data Protection
- **Tenant Isolation** - Cannot access other tenant's data
- **Schema Separation** - Platform/B2B/B2C logically isolated
- **Audit Logging** - Platform actions tracked in platform_audit_log

---

## Observability & Monitoring

### Structured Logging

All microservices use `structlog` for cloud-adaptive structured logging:

**Local Development:**
- Human-readable colored console output
- Key-value format for easy debugging

**Production (GCP/AWS):**
- JSON format compatible with cloud logging services
- Automatic severity mapping
- Trace context injection

**Request Tracing:**
- Every HTTP request gets unique `request_id`
- All logs for same request share the ID
- Enables distributed tracing across services
- Automatic context injection (HTTP metadata, user/tenant info)

**Log Structure:**
```json
{
  "severity": "INFO",
  "timestamp": "2025-12-01T07:11:42.717558Z",
  "message": "request_completed",
  "request_id": "abc-123-def-456",
  "http_method": "POST",
  "http_path": "/api/tenants",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "duration_ms": 45,
  "status_code": 200
}
```

**Configuration:**
- `LOG_ENVIRONMENT`: local, gcp, aws, production
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Environment-specific formatters auto-selected

### Future Monitoring

- [ ] OpenTelemetry traces
- [ ] Prometheus metrics
- [ ] Datadog/New Relic integration
- [ ] Real-time alerting

---

## Testing Architecture

### Backend Tests
- **Unit Tests** - Service layer logic
- **Integration Tests** - Full API flow with test DB
- **Unified Test App** - All routers combined for e2e testing

**Test Isolation:**
- Separate test database
- Fixtures create isolated test data
- Rollback after each test

### Frontend Tests
- **Component Tests** - React Testing Library
- **E2E Tests** - Playwright/Cypress (future)

---

## Build Strategy

### Unified Dockerfile
We use a single `backend/Dockerfile` with multi-stage builds to support all environments:

1.  **Base**: Common system dependencies.
2.  **Builder**: Installs Python dependencies (cached).
3.  **Test-Base**: Adds Playwright and test tools (cached).
4.  **Production Targets** (`b2b`, `platform`, `b2c`): Copy only service-specific code. Lean images.
5.  **Test Target** (`test`): Copies all code for e2e testing.

**Benefits:**
- Single source of truth
- Fast local testing (aggressive caching)
- Lean production images
- Consistent environment

---

## Directory Structure

### Backend
```
backend/
├── core/              # Shared infrastructure
│   ├── config.py
│   ├── database.py
│   ├── middleware/
│   └── utils/
├── services/
│   ├── b2b/          # B2B microservice
│   │   ├── main.py   # Entrypoint
│   │   ├── models/
│   │   ├── routers/
│   │   └── services/
│   ├── platform/     # Platform microservice
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   └── middleware/
│   ├── b2c/          # B2C microservice
│   │   └── main.py
│   └── domains/      # Domain logic
│       └── farming/
├── migrations/       # Database migrations
├── scripts/          # Admin CLI tools
└── tests/            # Test suite
    ├── test_app.py   # Unified test app
    └── e2e_api/      # Integration tests
```

### Frontend
```
frontend/src/
├── modules/          # Feature modules
│   ├── b2b/
│   ├── platform/
│   └── b2c/
├── components/       # Shared components
└── services/        # API clients
```

---

## Migration Strategy

### Current State
- ✅ Microservices implemented
- ✅ All tests passing (24/24)
- ✅ Docker compose configured
- ⚠️ Single database (intentional)

### Future Evolution
1. **Short Term** - API Gateway (nginx/traefik)
2. **Medium Term** - Kubernetes deployment
3. **Long Term** - Database per service (if needed)

---

For implementation details, see:
- [Development Guide](../guides/development.md)
- [Platform Admin Guide](../guides/platform-admin.md)
- [RBAC Documentation](./rbac.md)
