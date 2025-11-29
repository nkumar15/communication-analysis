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
- All B2B tables scoped by `tenant_id`
- PostgreSQL RLS policies enforce isolation
- Application sets `app.current_tenant_id` session variable

**Schema Isolation:**
- Platform admins isolated from B2B tenants
- B2C workspaces isolated from B2B enterprises
- Clear data boundaries

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
