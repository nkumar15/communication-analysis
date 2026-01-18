---
description: Manage separate isolated environments for Development (Ephemeral) and Demos (Persistent).
---

# Multi-Environment Workflow (Dev vs Demo)

This workflow separates your daily development environment from long-running demo environments.

**Features:**
- **Isolation**: Dev resets do not affect Demos. Demos do not affect each other.
- **Persistence**: Demo data is preserved until explicitly destroyed.
- **Conflict Prevention**: Only one environment runs at a time (on standard ports).

## 1. Development (Ephemeral)

Use this for daily coding, testing, and debugging.
**Project Name**: `saas-dev`

```bash
# Start Dev
make dev-up

# Reset Dev (Wipes DB, restarts, seeds default data)
make dev-reset

# Run Tests (Runs against Dev environment)
make test p=b2b case=bank
```

## 2. Demos (Persistent)

Use this for "Show & Tell". Data persists across restarts.
**Project Name**: `saas-demo-<CASE>`

```bash
# Start Bank Surveillance Demo (Resumes previous state)
make demo-up case=bank

# Start Finance Trader Demo (Stops Bank, starts Finance)
make demo-up case=finance

# Reset/Initialize a Demo (WIPES persistent data for that case)
make demo-init case=bank
```

## 3. Switching Environments

The system automatically stops conflicting environments.

1.  If you are in `dev-up` and run `make demo-up case=bank`, **Dev will stop**.
2.  If you are in `demo-up case=bank` and run `make demo-up case=finance`, **Bank will stop**.

## 4. Troubleshooting

**Check status of all containers:**
```bash
# Check Dev
./ops/scripts/env-manager.sh ps dev

# Check Demo
./ops/scripts/env-manager.sh ps demo bank
```

**Force Stop Everything:**
```bash
docker stop $(docker ps -aq)
```
