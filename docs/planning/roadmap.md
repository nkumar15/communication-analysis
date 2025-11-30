# Development Roadmap

## ✅ Completed Features (Phases 0-5)

All tenant onboarding phases complete! See [Completed Phases](./completed-phases.md) for detailed checklist.

**Major Features:**
- ✅ Multi-tenant architecture with SQLAlchemy ORM
- ✅ Automated tenant provisioning CLI
- ✅ Firebase GCIP multi-tenancy integration
- ✅ OIDC provider auto-configuration
- ✅ Email-based activation workflow
- ✅ Self-service tenant activation UI
- ✅ Role-based invitation system
- ✅ Complete documentation

**Current State:**
- Backend: FastAPI + PostgreSQL + SQLAlchemy
- Frontend: React + Firebase SDK
- Auth: Firebase GCIP with OIDC
- Email: Resend API with console fallback
- Admin UI: Complete dashboard with sidebar navigation
- Testing: Full E2E flows verified

**Recently Completed (2025-11-24):**

- ✅ **Complete Admin Dashboard Interface**
  - Sidebar navigation (Dashboard / User Management)
  - Top header with user profile dropdown
  - Professional layout wrapper for all admin pages
  - Logout functionality with user info display
  
- ✅ **Enhanced User Management UI**
  - Professional table design with search and filters
  - Tab navigation (Users / Pending Invitations)
  - Statistics dashboard (4 stat cards)
  - Color-coded role badges (Admin, Manager, Member)
  - Status badges (Active, Inactive, Pending, Expired)
  - Action menus (three-dot dropdowns)
  - Modal for inviting users
  - Clean data separation (no duplication between users and invitations)

- ✅ **User invitation system** - Admins can invite managers via email
  - Email domain validation
  - Invitation management UI (list, resend, cancel)
  - Public invitation acceptance page
  - SSO integration for invited users
  - Role assignment (manager role)

- ✅ **SaaS Super Admin Console** (2025-11-28)
  - Dedicated `/platform-login` for super admins
  - Dashboard with global stats (Tenants, Users)
  - Tenant Management (List, Create, Search)
  - "Login As" Impersonation for support
  - Security isolation from regular tenants

- ✅ **Microservices Architecture** (2025-11-29)
  - Split backend into 4 independent services (B2B, Platform, B2C, Domain)
  - Moved migrations to top-level
  - Updated Docker Compose for multi-service deployment
  - Created unified test app for e2e testing
  - All 24 integration tests passing

- ✅ **DevOps Foundation & Docker Optimization** (2025-11-29)
  - Unified multi-stage Dockerfile (b2b, platform, b2c, domain, test targets)
  - Fast build caching for development and testing
  - Interactive setup scripts (platform-seed, platform-create-admin, b2b-seed)
  - Makefile modernization (logs-*, shell-*, up-backend, dev workflows)
  - Frontend environment configuration (localhost API URLs)
  - Comprehensive documentation updates

- ✅ **Structured Logging System** (2025-12-01)
  - Cloud-adaptive logging with `structlog` library
  - Environment-specific formatters (local, GCP, AWS, production)
  - Automatic request tracing with correlation IDs
  - FastAPI middleware for context injection (request_id, HTTP metadata, user context)
  - Integrated across all 4 microservices (b2b, platform, b2c, domain)
  - Human-readable output for development, JSON for production
  - Ready for cloud deployment (GCP Cloud Logging, AWS CloudWatch)

- ✅ **E2E Browser Testing Infrastructure** (2025-11-28)
  - Playwright integration with Docker
  - Real Firebase authentication with custom tokens
  - `make e2e-browser` command
  - Basic page load tests passing (3/3)
  - Ready for full test scenario implementation

---

## ⏭️ Next Priority

### Phase 4: CI/CD & Observability
- [ ] GitHub Actions CI/CD pipeline
- [ ] OpenTelemetry traces and metrics
- [ ] Automated deployment workflows
- [ ] Log aggregation integration (Datadog, New Relic)

---

## 🚧 Known Issues / Technical Debt

*(Add items as you discover them)*

Example:
- [ ] Add database connection pooling configuration
- [ ] Implement API rate limiting
- [ ] Add comprehensive error logging

---

## 📋 Product Backlog

### 🔴 High Priority (Next 1-2 Months)

#### Security & Compliance
- [ ] **Audit logging for security events**
  - Track login attempts, role changes, permission modifications
  - Export audit logs for compliance (SOC2, GDPR)
  - Built-in log viewer in admin dashboard
  - Estimated effort: 1 week

- [ ] **Multi-factor authentication (MFA)**
  - Firebase MFA integration
  - SMS/TOTP support
  - Per-tenant MFA enforcement policies
  - Estimated effort: 2 weeks

- [ ] **API rate limiting**
  - Per-tenant and per-user rate limits
  - Redis-based throttling
  - Rate limit headers in API responses
  - Estimated effort: 3 days

#### User Management
- [ ] **Bulk user operations**
  - CSV import/export
  - Bulk invite via email list
  - Bulk role assignment
  - Estimated effort: 1 week



### 🟡 Medium Priority (3-6 Months)

#### RBAC Enhancement (See detailed plan below)
- [ ] **Create Role API** (Day 2 Requirement)
  - `POST /api/roles` endpoint for tenant admins
  - Allow creation of custom roles with specific permissions
- [ ] **Configurable tenant-specific RBAC**
  - Custom role creation UI
  - Permission matrix management
  - Role cloning and templates
  - Estimated effort: 3-4 weeks

#### Platform Features
- [ ] **Organization settings page**
  - Tenant branding (logo, colors)
  - Email templates customization
  - SSO provider management UI
  - Estimated effort: 2 weeks

- [ ] **API key management**
  - Generate API keys for integrations
  - Scoped permissions per key
  - Usage tracking and rotation
  - Estimated effort: 1 week

- [ ] **Usage analytics dashboard**
  - Active users tracking
  - Login frequency charts
  - Resource usage metrics
  - Estimated effort: 2 weeks

### 🟢 Low Priority / Future Enhancements

- [ ] **Advanced user roles**
  - Hierarchical roles (supervisor → manager → worker)
  - Temporary role assignments (time-limited)
  - Role delegation
  
- [ ] **Custom branding per tenant**
  - White-label frontend
  - Custom domain support
  - Email template editor

- [ ] **SSO with SAML** (in addition to OIDC)
  - SAML 2.0 provider support
  - Azure AD, Okta SAML integration
  
- [ ] **Mobile app support**
  - React Native companion app
  - Mobile-optimized dashboard
  - Push notifications

- [ ] **Advanced data export**
  - Scheduled reports
  - Custom report builder
  - PDF/Excel export

---

## 🎨 Feature Deep-Dive: Configurable Multi-Tenant RBAC

**Status:** Backlog (Medium Priority)  
**Estimated Effort:** 3-4 weeks  
**Dependencies:** Existing RBAC foundation (`rbac_models.py`)

### Problem Statement
Currently, roles (`admin`, `field_manager`, `field_worker`) are **hardcoded** in both backend and frontend. Tenants cannot:
- Create custom roles (e.g., "Regional Supervisor", "Data Analyst")
- Define their own permission sets
- Adapt the system to their specific organizational structure

### Proposed Solution: Hybrid RBAC System

#### Architecture (3-Tier Role System)

| Tier | Scope | Examples | Deletable? | Customizable Permissions? |
|------|-------|----------|------------|---------------------------|
| **System Roles** | Platform-wide | `platform_admin`, `tenant_owner` | ❌ No | ❌ No |
| **Default Roles** | Per-tenant (seeded) | `admin`, `manager`, `member` | ⚠️ Only if unused | ✅ Yes |
| **Custom Roles** | Per-tenant (user-created) | `Regional Supervisor`, `Auditor` | ✅ Yes | ✅ Yes |

#### Database Changes Required

```sql
-- Already exists in rbac_models.py ✅
-- Just needs these additions:

ALTER TABLE roles ADD COLUMN is_custom BOOLEAN DEFAULT false;
ALTER TABLE roles ADD COLUMN created_by UUID REFERENCES users(id);

-- Optional: Tenant-specific resource visibility
CREATE TABLE tenant_resources (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    resource_id UUID REFERENCES resources(id),
    is_enabled BOOLEAN DEFAULT true
);
```

#### Backend API Endpoints

```python
# Role Management
POST   /api/roles                               # Create custom role
GET    /api/roles                               # List tenant roles
GET    /api/roles/{role_id}                     # Get role + permissions
PUT    /api/roles/{role_id}                     # Update role metadata
DELETE /api/roles/{role_id}                     # Delete custom role

# Permission Management  
POST   /api/roles/{role_id}/permissions         # Assign permissions
DELETE /api/roles/{role_id}/permissions/{perm_id}  # Revoke permission

# Discovery
GET    /api/resources                           # List available resources
GET    /api/actions                             # List available actions
```

#### Frontend Components

1. **Role Management Page** (`/admin/roles`)
   - Table of all roles (system + default + custom)
   - "Create Role" button (admin only)
   - Edit/Delete actions per role
   
2. **Role Editor Modal**
   - Role name, display name, description
   - Permission matrix (Resources × Actions grid)
   - "Clone from existing role" option
   
3. **Permission Enforcement**
   - Replace hardcoded role checks with `useHasPermission(resource, action)` hook
   - Conditionally render UI elements based on permissions

#### Implementation Phases

**Phase 1: Backend Foundation (Week 1)**
- [ ] Create `rbac_service.py` with permission checking logic
- [ ] Add database migration for new columns
- [ ] Implement role CRUD API endpoints
- [ ] Add permission assignment endpoints
- [ ] Create `@require_permission` decorator for routes

**Phase 2: Permission Enforcement (Week 2)**
- [ ] Replace hardcoded role checks in all routers
- [ ] Add permission caching in JWT tokens
- [ ] Update frontend auth service to parse permissions
- [ ] Create `useHasPermission` React hook

**Phase 3: Admin UI (Week 3)**
- [ ] Build role management page
- [ ] Create role editor modal with permission matrix
- [ ] Add role cloning functionality
- [ ] Implement real-time permission updates

**Phase 4: Testing & Documentation (Week 4)**
- [ ] Write unit tests for RBAC service
- [ ] E2E tests for custom role creation
- [ ] Update API documentation
- [ ] Create user guide for configurable RBAC

#### Migration Strategy

- **Backward Compatible:** Existing hardcoded roles become "default roles"
- **Zero Downtime:** New system works alongside old until fully migrated
- **Gradual Rollout:** Enable configurable RBAC per tenant via feature flag

#### Benefits

✅ **For SaaS Platform:**
- Differentiation from competitors
- Enterprise-ready feature
- Higher pricing tier opportunity

✅ **For Tenants:**
- Adapt to their org structure
- Self-service (reduce support tickets)
- Granular access control

✅ **For Developers:**
- Cleaner code (no hardcoded checks)
- Easier to add new features
- Better security (principle of least privilege)

#### Related Documents
- Database schema: `backend/app/rbac_models.py`
- Current role usage: `backend/app/middleware/auth.py`
- Frontend role checks: `frontend/src/services/authService.js`

---

## 🎯 Next Development Session

**Start your next session with:**
```
"Review docs/ROADMAP.md and docs/development-guide.md. 
I want to add [describe feature]. Check current architecture first."
```

**Before implementing:**
1. Check if similar functionality exists
2. Review database schema in migrations/
3. Look at existing services in backend/app/services/
4. Check frontend components in frontend/src/components/

---

## 📖 Documentation Structure

All documentation is in your repository:

```
docs/
├── COMPLETED_PHASES.md    # Detailed task checklist
├── ROADMAP.md             # This file - planning & features
├── development-guide.md   # Complete dev & testing guide
├── testing-workflow.md    # Testing procedures
└── e2e-activation-test.md # Activation flow testing
```

**Always keep ROADMAP.md updated** as you add features!

---

## 🔍 Architecture Reference

**Database:**
- Migrations: `backend/app/migrations/`
- Models: `backend/app/db_models.py`
- Services: `backend/app/services/`

**API:**
- Routes: `backend/app/routers/`
- Auth middleware: `backend/app/middleware/auth.py`

**Frontend:**
- Components: `frontend/src/components/`
- Services: `frontend/src/services/`
- Firebase: `frontend/src/services/firebaseAuthService.js`

**CLI:**
- Tenant provisioning: `backend/cli/tenant_cli.py`
- Email service: `backend/cli/email_service.py`

---

## 💡 Development Tips

1. **Use the CLI for testing:**
   ```bash
   make reset-db  # Interactive reset + tenant creation
   ```

2. **Check existing patterns:**
   - Service layer for business logic
   - Pydantic models for validation
   - SQLAlchemy ORM for database
   - Dependency injection in FastAPI

3. **Testing workflow:**
   - Backend: Check logs with `make logs`
   - Database: Use `make db-shell` for SQL queries
   - Frontend: Browser dev tools + React DevTools

4. **Documentation:**
   - Update ROADMAP.md when adding features
   - Add to development-guide.md if architectural
   - Keep README.md high-level

---

**Last Updated:** 2025-12-01  
**Current Version:** Phase 4 Structured Logging Complete
