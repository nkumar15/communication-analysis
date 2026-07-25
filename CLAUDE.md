# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Request Classification

Before implementing any task, classify it into one of these types (execute in this order when multiple apply):
1. `security_audit` / `db_migration_or_schema_change` — safety and schema first
2. `backend_service_logic_change` — business logic
3. `backend_endpoint_change` — API wiring
4. `frontend_change`
5. `test_add_or_test_fix`
6. `documentation_change`
7. `environment_stabilization` / `makefile_change`

Refer to `AGENTS.md` for the full routing matrix (rules → workflows → skills per type).

---

## Common Commands

All common dev tasks are in the `Makefile`. Run `make help` or browse the Makefile for targets.

### Infrastructure
```bash
make up              # Build and start the full stack (postgres, redis, elasticsearch, minio, nginx, B2B API/worker, Bank Surveillance domain API/worker, frontend)
make down            # Stop all services
make restart         # Restart everything
```

### Database
```bash
make db-recreate     # Drop + recreate DB with migrations (destructive)
make migrate-schema  # Run SQL migrations only
make db-setup-auth   # Setup Row-Level Security
make db-shell        # Open PostgreSQL shell
```

### Seeding
```bash
make b2b-demo-bank   # Full demo: recreate DB, start services, seed roles, onboard demo tenant
make seed-all        # Seed RBAC roles only (services must already be running)
```

### Frontend Dev Server
```bash
# From frontend/ directory
npm run start:b2b       # http://localhost:3000

# Or via Makefile
make web-b2b
```

### Testing
```bash
# Top-level entry points
make test-api                                        # Full backend pytest suite (db-recreate + seed + run)
make test-api path=tests/b2b/api/foundation          # Scoped to a specific path
make test-ui                                         # Automated Playwright browser tests

# Scoped backend suites
make test-b2b-foundation-only                        # B2B foundation tests only
make test-b2b-bank-only                              # Bank Surveillance tests only
make test-b2b-bank                                   # Foundation + Bank Surveillance combined
make test-all-foundation                             # Alias for test-b2b-foundation-only

# Single test file (services must already be running via make up):
docker-compose --profile test-api run --rm e2e-tests pytest tests/b2b/api/foundation/test_users.py -v

# Load testing
make load-test-b2b DURATION=1m      # 50 concurrent users
```

### Security Scanning
```bash
make sast-scan        # Bandit + Semgrep + Trivy
make dast-scan        # OWASP ZAP baseline scan
```

---

## Architecture Overview

### System Structure

Two FastAPI microservices, served via nginx gateway (`:8080`):

| Service | Port | Responsibility |
|---|---|---|
| B2B API | 8000 | Tenant management, RBAC, teams, SSO |
| B2B Domain API | 8003 | Bank Surveillance (the only domain in this repo) |

Frontend is a **single React/Webpack codebase** building one portal (`PORTAL=b2b`).

### Backend Module Layout

Each module follows the same structure:
```
modules/b2b/
├── main.py          # FastAPI app definition + routers registration
├── routers/         # HTTP layer — thin, no business logic
├── services/        # Business logic — fat, all validation here
├── models/          # SQLAlchemy ORM models
├── schemas/         # Pydantic DTOs (EntityCreate, EntityUpdate, EntityResponse)
├── rbac/            # RBAC rules and permission checks
└── tasks/           # Celery task definitions
```

The domain module lives at `modules/domains/b2b/bank_surveillance/` and follows the same structure.

Shared foundations:
- `core/` — config, db sessions, base models, lifespan hooks
- `infrastructure/` — auth (Firebase), email (Resend/SES/console), monitoring (OTel/Sentry)
- `plugins/` — RBAC extension plugins (geo, data classification, hierarchical teams)
- `workers/{b2b,b2b_domain}_worker/` — Celery workers

### Frontend Module Layout

```
frontend/src/
├── core/               # Shared: API clients, Firebase auth, hooks, base components
│   ├── api/            # b2bClient.js, b2bDomainClient.js (auto token attached)
│   ├── firebase/       # authService.js, tenantManager.js
│   └── hooks/          # useAuth.js and other cross-cutting hooks
├── modules/
│   ├── b2b/            # B2B portal pages, components, layouts
│   └── domains/        # Domain-specific UI (surveillance/)
└── shared/             # Utilities and constants
```

### Multi-Tenancy

- Firebase GCIP provides authentication; each customer gets an isolated Firebase tenant.
- PostgreSQL Row-Level Security (RLS) is the primary isolation mechanism — `rls_service.set_tenant_context()` must be called before any query.
- **Every service query must also include an explicit `.where(Model.tenant_id == tenant_id)` filter** as a secondary defense — never trust a client-supplied `tenant_id`.

---

## Backend Guardrails (Mandatory)

These apply to every backend write path:

1. **Thin routers, fat services** — routers extract context and call services; all logic lives in services.
2. **RBAC enforcement** — check permissions via `rbac_service` or dependency injection at the router level.
3. **Tenant isolation** — both RLS context AND explicit `tenant_id` filter in every query.
4. **Commit before side effects** — `await db.commit()` in the router before triggering Celery tasks or emails.
5. **Audit logging** — all Create/Update/Delete actions must trigger the async `persist_audit_log` Celery task after commit. Schema: `tenant_id`, `actor_id`, `event_type` (noun.verb), `resource_id`.
6. **No PII in logs** — never log emails, names, or secrets.

---

## Code Conventions

### Python
- **Type hints are mandatory** on all function arguments and return values.
- Use `async def` for all I/O-bound operations.
- Google-style docstrings for modules, classes, and public methods.
- Use `from infrastructure.logging import get_logger`; `print()` is forbidden.
- SQLAlchemy 2.0 style: `select(Model).where(...)`. Prevent N+1 with `selectinload`.
- Pydantic schema naming: `EntityCreate`, `EntityUpdate`, `EntityResponse`.
- Celery tasks: only pass primitive IDs (UUID/int), never SQLAlchemy objects. Tasks must be idempotent.
- All DB tables: `UUID` primary keys, `tenant_id` with index, `created_at`/`updated_at` timestamps, FK for relations (no IDs in JSONB).
- Concurrent read-modify-write: use `with_for_update()`.

### React / Frontend
- Pages (`pages/`) are route handlers with minimal logic; business logic goes into services or hooks.
- Server state via **TanStack Query**; shared global state via React Context; local state via `useState`/`useReducer`.
- All API calls must go through the appropriate client (`b2bClient` for foundation, `b2bDomainClient` for Bank Surveillance).

---

## Key Access Points (Local Dev)

| Service | URL |
|---|---|
| B2B Portal | http://localhost:3000 |
| API Gateway / Swagger | http://localhost:8080 |

---

## Agent Tools (`.agent/`)

This repo has a structured agent automation system:
- `.claude/rules/` → `shared-rules/` — always-on coding, architecture, testing, and documentation standards
- `.agent/workflows/` — step-by-step guides for common change types (new endpoint, test audit, security audit, E2E)
- `.claude/skills/` → `shared-skills/` — code generation tools: `pytest-test-generator`, `pydantic-schema-generator`, `db-inspector`, `product-doc-generator`, `doc-generator`, `system-doc-maintainer`

Skills live in `shared-skills/` (canonical location) and are symlinked into `.claude/skills/` and `.agent/skills/` so Claude, Codex, and other agents share the same definitions.

Always-on rules for Python/backend work: `coding-standards`, `python-developer`, `backend-architecture`, `observability-standards`.
For Celery tasks/workers: also apply `celery-standards`.

Consult the relevant rule/workflow when working in that area.

## Enforcement Hooks (`.claude/`)

Post-edit hooks run automatically after every file edit and warn on:
- Direct DB queries inside router files (business logic belongs in services)
- `print()` calls in non-test Python files (use `get_logger()`)
- ORM objects passed as Celery task arguments (use primitive IDs only)
- New Alembic migrations missing `tenant_id` / UUID / timestamp columns
- Services importing from routers (layer violation)

Hooks are defined in `.claude/settings.json` and executed by `.claude/hooks/post_edit_check.sh`.
