# Backend Testing Runbook

Quick reference for running tests. Start here before opening the Makefile.

---

## Mental Model

Tests are organized across three tiers and three portals:

```
Tier               B2B                        B2C                    Platform
─────────────────────────────────────────────────────────────────────────────
API (integration)  tests/b2b/api/             tests/b2c/api/         tests/platform/api/
                   ├── foundation/            ├── foundation/         (no domain split)
                   └── use_cases/             └── use_cases/
Service tests      tests/b2b/services/        tests/b2c/services/    tests/platform/services/
                   ├── foundation/            ├── foundation/
                   └── use_cases/             └── use_cases/
Unit tests         tests/b2b/units/           tests/b2c/units/       tests/platform/units/
```

**Foundation** — core platform features: auth, invitations, teams, roles, billing, RBAC, audit logs.
Seeded with base roles only. No `USE_CASE` env var required.

**Use cases** — domain verticals (bank_surveillance, task_management, finance_trader).
Seeded with `USE_CASE=<domain>`. Adds domain-specific roles and resources on top of the base seed.

---

## Pick Your Scenario

| I'm working on… | Command |
|---|---|
| B2B auth, invitations, teams, roles, billing | `make test-b2b-foundation-only` |
| Bank surveillance domain features | `make test-b2b-bank-only` |
| Bank surveillance + full B2B foundation | `make test-b2b-bank` |
| B2C workspaces, subscriptions | `make test-b2c-foundation-only` |
| Platform admin / tenant management | `make test-platform-foundation-only` |
| Everything (CI / pre-merge) | `make test-all-foundation` |

Each `make` target handles `db-recreate → up → seed → pytest` automatically.

---

## Single Test / TDD Loop

When iterating on a fix, you don't need to recreate the DB every time.

### Phase A — DB already seeded (fast inner loop)

```bash
# Run one test file
docker-compose run --rm e2e-tests pytest tests/b2b/api/foundation/organization/test_users.py -v

# Run one specific test
docker-compose run --rm e2e-tests pytest \
  tests/b2b/api/foundation/organization/test_users.py::TestUserManagement::test_deactivate_self_forbidden -v

# Run by marker
docker-compose run --rm e2e-tests pytest tests/b2b/ -m security -v

# Unit tests — no DB needed, run locally outside Docker
cd backend && pytest tests/b2b/units/ -v
```

### Phase B — Reset DB first (when seed state is stale or wrong)

```bash
make db-recreate && make up && sleep 5 && make seed-all
# then run any Phase A command above
```

### Domain tests — pass USE_CASE through

```bash
make db-recreate && make up && sleep 5 && make seed-all USE_CASE=bank_surveillance

docker-compose run --rm -e USE_CASE=bank_surveillance e2e-tests \
  pytest tests/b2b/api/use_cases/bank_surveillance/test_alerts.py -v
```

---

## Seeding Reference

| Test area | Seed command | Roles seeded |
|---|---|---|
| Foundation (all portals) | `make seed-all` | owner, admin, member, team_contributor, team_manager, team_viewer |
| Bank surveillance | `make seed-all USE_CASE=bank_surveillance` | above + surveillance_chief, surveillance_analyst, operations_maker, operations_checker |

Using a domain role in a foundation test (or vice versa) will produce a 403 — check this first when permissions fail unexpectedly.

---

## Fixtures Quick Reference

Defined in `backend/tests/conftest.py`:

| Fixture / Helper | What it gives you |
|---|---|
| `db_session` | Per-test async DB session, auto-rolled back after each test |
| `api_client` | `httpx.AsyncClient` wired to all routers (B2B, B2C, Platform, Domain) |
| `create_test_tenant(db_session)` | Active tenant with RLS context set |
| `create_test_user(db_session, tenant_id, role=...)` | User with a specific role slug |
| `create_test_invitation(db_session, tenant_id)` | Pending invitation |
| `encode_mock_jwt(uid, email, tenant_id)` | Mock Firebase JWT for `Authorization: Bearer` headers |

Domain tests have their own conftest that extends these. For example:
`tests/b2b/api/use_cases/bank_surveillance/conftest.py` adds bank-specific resource fixtures.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 403 on all permission tests | Wrong roles seeded | Match seed tier to test tier (foundation vs domain) |
| 401 on all requests | Tenant not active or DB not seeded | `make seed-all` |
| `asyncio event loop` error | pytest-asyncio misconfigured | Ensure `asyncio_mode = auto` in `backend/pytest.ini` |
| `ImportError` running unit tests | Wrong working directory | Run from `backend/`, not project root |
| Unique constraint violation | Stale rows from a previous partial run | `make db-recreate` |
| Domain role not found | Foundation seed used for domain test | Add `USE_CASE=bank_surveillance` to seed and pytest run |
