---
description: Manage separate isolated environments for Development (Ephemeral) and Demos (Persistent).
---

# Multi-Environment Workflow (Dev vs Demo)

This workflow separates your daily development environment from long-running demo environments.

## Quick Reference

| Command | Purpose |
| :--- | :--- |
| `make dev-up` | Start Dev (ephemeral) |
| `make dev-reset` | Wipe Dev DB, restart, seed |
| `make demo-up case=bank` | Start Bank Demo (persistent) |
| `make demo-up case=finance` | Switch to Finance Demo |
| `make demo-init case=bank` | Reset/Initialize a Demo |

---

## 1. How Isolation Works

### Docker Project Names

The magic is `COMPOSE_PROJECT_NAME`. Same `docker-compose.yml`, different universes:

```bash
docker-compose -p saas-dev up         # Dev
docker-compose -p saas-demo-bank up   # Bank Demo
docker-compose -p saas-demo-finance up # Finance Demo
```

### Automatic Separation

| Component | Dev (`saas-dev`) | Demo (`saas-demo-bank`) |
| :--- | :--- | :--- |
| **Network** | `saas-dev_default` | `saas-demo-bank_default` |
| **DB Volume** | `saas-dev_postgres_data` | `saas-demo-bank_postgres_data` |
| **Container** | `saas-dev-postgres-1` | `saas-demo-bank-postgres-1` |

### Same Config, Different Data

```env
# .env (shared by ALL environments)
DATABASE_URL=postgresql://postgres:postgres_secret@postgres:5432/saas_demo_db
```

- In Dev: `postgres` → `saas-dev-postgres-1`
- In Demo: `postgres` → `saas-demo-bank-postgres-1`

**No separate DATABASE_URLs needed.** Docker DNS handles it.

---

## 2. Testing

> [!IMPORTANT]
> Tests always run against the **Dev** environment to avoid polluting Demo data.

### Quick Commands

| Command | Scope | Speed |
| :--- | :--- | :--- |
| `make test-api` | All API tests | Medium |
| `make test-b2b` | All B2B (Core + Use Cases) | Slow |
| `make test-b2b-core-only` | Core B2B only | Fast |
| `make test-b2b-bank-fast` | Bank tests (no DB reset) | Fast |
| `make test-browser` | All E2E browser tests | Slow |
| `make test-coverage` | All tests + coverage report | Slow |

### API Tests (Docker)

```bash
# All API tests
make test-api

# B2B Core only (fastest)
make test-b2b-core-only

# B2B with Bank Surveillance (full reset)
make test-b2b-bank-full

# B2B Bank (fast mode, no reset)
make test-b2b-bank-fast

# Run specific test file
docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/core/test_teams.py -v
```

### Browser Tests (E2E)

```bash
# All browser tests (headless in Docker)
make test-browser

# Specific product
make test-browser-b2b
make test-browser-b2c
make test-browser-platform

# Local headed mode (for debugging)
make local-test-browser-b2b
```

### Domain Tests

```bash
# RAG domain tests
make test-domain-rag
```

### Load Tests

```bash
# B2B load test (50 users, 30s)
make load-test-b2b DURATION=30s

# B2C load test
make load-test-b2c DURATION=30s
```

### Coverage Report

```bash
# HTML report
make test-coverage

# XML for CI
make test-coverage-xml
```

---

## 3. Development (Ephemeral)

Reset frequently. Data is disposable.

```bash
# Start
make dev-up

# Reset (Wipes DB, restarts, seeds)
make dev-reset

# Run Tests
make test p=b2b case=bank
```

---

## 4. Demos (Persistent)

Data survives restarts. Only one runs at a time.

```bash
# Start Bank Demo (Resumes previous state)
make demo-up case=bank

# Switch to Finance (Stops Bank automatically)
make demo-up case=finance

# Reset a Demo (DESTRUCTIVE)
make demo-init case=bank
```

---

## 5. Volume Management

### List Volumes
```bash
docker volume ls | grep saas
```

### Backup a Demo (pg_dump)
```bash
docker exec saas-demo-bank-postgres-1 \
  pg_dump -U postgres saas_demo_db > bank_backup.sql
```

### Restore Backup
```bash
docker exec -i saas-demo-finance-postgres-1 \
  psql -U postgres saas_demo_db < bank_backup.sql
```

### Clone Volume (Copy Demo → Demo)
```bash
# Stop both projects first
docker-compose -p saas-demo-bank stop
docker-compose -p saas-demo-finance stop

# Clone postgres volume
docker run --rm \
  -v saas-demo-bank_postgres_data:/src:ro \
  -v saas-demo-finance_postgres_data:/dst \
  alpine sh -c "rm -rf /dst/* && cp -a /src/. /dst/"
```

---

## 6. Environment Files Strategy

### Current State (Problem)
- 21 `environment:` blocks in `docker-compose.yml`
- Same vars repeated 6-11 times

### Recommended Structure
```
.env                    # Core infra (DB, Redis) - shared
.env.secrets            # API keys (gitignored)
.env.local.example      # Template for developers
```

### docker-compose.yml (Use YAML Anchors)
```yaml
x-common-db: &common-db
  DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${POSTGRES_DB}
  REDIS_URL: redis://redis:6379/0

services:
  b2b-api:
    env_file: [.env, .env.secrets]
    environment:
      <<: *common-db
      SERVICE_NAME: b2b-api
```

---

## 7. Scripts (To Be Implemented)

### `ops/scripts/env-manager.sh`
Manages Docker project switching with conflict prevention.

### `ops/scripts/reset-db.sh`
Handles DB drop/create/migrate/seed for active project.

---

## 8. Troubleshooting

**Check running containers:**
```bash
docker-compose -p saas-dev ps
docker-compose -p saas-demo-bank ps
```

**Force stop everything:**
```bash
docker stop $(docker ps -aq)
```

**Prune unused volumes:**
```bash
docker volume prune
```
