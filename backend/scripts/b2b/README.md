# B2B Scripts

RBAC and tenant configuration for multi-tenant B2B SaaS.

## Directory Structure

```
scripts/b2b/
├── base/                          # Base SaaS layer (always loaded)
│   ├── actions.yaml               # Universal actions (read, write, delete, etc.)
│   ├── saas_resources.yaml        # Platform resources (users, teams, billing, etc.)
│   ├── saas_roles.yaml            # Tenant roles (owner, admin, member, viewer)
│   └── team_roles_fallback.yaml   # Team roles (used if use case has none)
│
├── use_cases/                     # Business-specific configurations
│   ├── bank_surveillance/         # ⭐ PRIMARY (plugins, custom roles)
│   ├── marketing_agency/          # Marketing domain
│   └── task_management/           # Project/task domain
│
├── seed_rbac.py                   # Main seeding script
├── seed_subscription_plans.py     # Subscription tier seeding
├── tenant_onboard.py              # Tenant creation workflow
└── subscription_plans.yaml        # Tier definitions
```

## Seeding Flow

```
Base Layer (always)          Use Case Layer (configurable)
─────────────────────        ────────────────────────────
base/actions.yaml        +   {use_case}/resources.yaml
base/saas_resources.yaml +   {use_case}/team_roles.yaml  (replaces fallback)
base/saas_roles.yaml     +   {use_case}/plugins.yaml     (if applicable)
base/team_roles_fallback.yaml (skipped if use case has team_roles)
```

## Usage

```bash
# Base-only seeding (for core platform testing)
python scripts/b2b/seed_rbac.py  # No USE_CASE = base roles only

# Domain seeding (for production or use case testing)
USE_CASE=bank_surveillance python scripts/b2b/seed_rbac.py
USE_CASE=marketing_agency python scripts/b2b/seed_rbac.py
USE_CASE=task_management python scripts/b2b/seed_rbac.py
```

## Testing

For detailed testing documentation, see [backend/tests/README.md](../../tests/README.md).

Tests are organized into **2 layers**:
1. **Core Platform** (base roles only) - `tests/e2e_api/b2b/core/`
2. **Use Cases** (domain roles) - `tests/e2e_api/b2b/use_cases/`

```bash
# Core tests (no USE_CASE)
make test-b2b-core-only

# Use case tests (with USE_CASE)
make test-b2b-bank-use-case

# Full suite
make test-b2b-all
```

## Use Case Feature Matrix

| Use Case | Team Roles | Plugins | Domain Resources |
|----------|-----------|---------|------------------|
| `bank_surveillance` | Custom | All 3 | communications, investigations |
| `marketing_agency` | Custom | None | campaigns, social_posts |
| `task_management` | Fallback | None | projects, tasks, comments |

## Customization

To create a new use case:

1. Copy an existing one: `cp -r use_cases/task_management use_cases/your_domain`
2. Edit `resources.yaml` with your domain resources
3. Edit `team_roles.yaml` if you need custom team roles
4. Run: `USE_CASE=your_domain python scripts/b2b/seed_rbac.py`
