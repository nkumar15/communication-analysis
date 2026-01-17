# Backend Shared Code Structure

## Scope
This structure applies to **shared/reusable code** located outside of module-specific folders (`modules/b2b`, `modules/b2c`).

---

## Core (`backend/core/`)
Framework-level utilities shared across ALL modules.

| Item | Purpose |
|------|---------|
| `config.py` | Application settings (Pydantic Settings) |
| `constants.py` | Global constants and enums |
| `db/` | Database session, base models, RLS service |
| `middleware/` | Shared request middleware |
| `rbac/` | Plugin system base classes |
| `utils/` | Generic utilities (time, hashing) |

**Rule**: Code here must be **module-agnostic**. No B2B/B2C-specific logic.

---

## Infrastructure (`backend/infrastructure/`)
External service integrations.

| Folder | Purpose |
|--------|---------|
| `auth/` | Firebase/Auth0 integration |
| `email/` | Email service (SendGrid, SMTP) |
| `payment/` | Stripe integration |
| `logging/` | Structured logging (structlog) |
| `monitoring/` | Observability (metrics, tracing) |
| `factories/` | Service factory patterns |

**Rule**: Infrastructure code wraps third-party SDKs. Business logic does NOT belong here.

---

## Migrations (`backend/migrations/`)
Alembic database migration scripts.

| Folder | Purpose |
|--------|---------|
| `versions/` | Individual migration files |
| `b2b/` | B2B schema-specific migrations (if separated) |
| `b2c/` | B2C schema-specific migrations (if separated) |

**Rule**: Never edit existing migrations. Create new ones for changes.

---

## Plugins (`backend/plugins/`)
RBAC extension plugins for enterprise features.

| Folder | Purpose |
|--------|---------|
| `hierarchical_teams/` | Team hierarchy traversal |
| `geographic_boundaries/` | Region-based access control |
| `data_classification/` | Sensitivity-based access control |

**Rule**: Each plugin MUST implement `RBACPlugin` interface from `core/rbac/`.

---

## Scripts (`backend/scripts/`)
Seed data, configuration files, and CLI utilities.

| Folder | Purpose |
|--------|---------|
| `b2b/` | B2B RBAC configs, subscription plans, use cases |
| `b2b/core/` | System roles (don't edit) |
| `b2b/domain/` | Production tenant/team roles |
| `b2b/use_cases/` | Demo/test configurations |
| `b2c/` | B2C seed data |
| `platform/` | Platform-level configs |

**Rule**: YAML files define declarative configs. Python scripts seed data.

---

## Workers (`backend/workers/`)
Celery background task definitions.

| Folder | Purpose |
|--------|---------|
| `b2b_worker/` | B2B async tasks (emails, audits) |
| `b2c_worker/` | B2C async tasks |
| `domain_worker/` | Cross-module domain tasks |

**Rule**: Workers must be idempotent. Tasks may be retried.
