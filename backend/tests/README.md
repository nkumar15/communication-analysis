# Backend Testing Guide

This directory contains the automated test suite for the Enterprise SSO backend.

## 📁 Directory Structure

```
backend/tests/
├── conftest.py             # Global fixtures (DB session, API client)
├── pytest.ini              # CRITICAL: Configures session-scoped event loop
├── e2e_api/
│   ├── b2b/
│   │   ├── core/           # 🌍 CORE Platform Tests (use base roles)
│   │   └── use_cases/      # 🏢 DOMAIN Tests (use domain-specific roles)
│   └── platform/
└── domain/                 # Isolated domain logic tests
```

## 🧪 Testing Methodology

### 1. Layered Test Architecture

We use a **2-Layer Testing Strategy** to separate platform from domain:

**Layer 1: Core Platform Tests** (`tests/e2e_api/b2b/core/`)
- Tests platform features (auth, teams, billing, settings)
- Uses **base roles only**: `owner`, `admin`, `member`, `team_contributor`
- Runs with **NO USE_CASE** set (base-only seeding)
- Independent of domain-specific features

**Layer 2: Use Case Tests** (`tests/e2e_api/b2b/use_cases/`)
- Tests domain-specific features (banking, marketing, etc.)
- Uses **domain roles**: `surveillance_chief`, `operations_maker`, etc.
- Runs with **USE_CASE=bank_surveillance** (domain seeding)
- Builds on verified core functionality

### 2. Seeding Strategy

**Base-Only Seeding** (for core tests):
```bash
# Seeds: owner, admin, member, team_contributor, team_manager, team_viewer
python scripts/b2b/seed_rbac.py  # No USE_CASE
```

**Domain Seeding** (for use case tests):
```bash
# Seeds: base roles + domain roles + plugins
USE_CASE=bank_surveillance python scripts/b2b/seed_rbac.py
```

### 3. Pytest Configuration (CRITICAL)

We use a **Session-Scoped Database Engine** (`test_db_engine`) in `conftest.py`.
To avoid `RuntimeError: Task attached to a different loop`, we MUST configure `pytest-asyncio` to use a session-scoped event loop.

**backend/pytest.ini**:
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
```

## 🚀 Running Tests

### Core Platform Tests
```bash
# Using Make target (recommended)
make test-b2b-core-only

# Manual
docker compose run --rm b2b-api python scripts/b2b/seed_rbac.py
docker compose run --rm e2e-tests pytest tests/e2e_api/b2b/core/ -v
```

### Use Case Tests
```bash
# Bank surveillance
make test-b2b-bank-use-case

# Manual
USE_CASE=bank_surveillance docker compose run --rm b2b-api python scripts/b2b/seed_rbac.py
USE_CASE=bank_surveillance docker compose run --rm e2e-tests \
  pytest tests/e2e_api/b2b/use_cases/bank_surveillance/ -v
```

### Full Suite
```bash
make test-b2b-all  # Runs core + all use cases
```

## 🛠 Troubleshooting

- **RuntimeError: Task pending...**: Check `pytest.ini` exists and sets `asyncio_default_fixture_loop_scope = session`.
- **403 Forbidden**: Ensure correct roles are seeded for the test layer you're running.
- **Role not found**: Core tests should use base roles only; domain tests use domain roles.
