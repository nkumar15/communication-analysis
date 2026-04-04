---
trigger: model_decision
description: This rule should be applied when any changes are required in Makefile commands, such as new targets, changing existing targets etc
---

# Makefile Standards & Best Practices

This document outlines the standards for maintaining the `Makefile` in the Enterprise SSO project. All changes to the Makefile must adhere to these guidelines to ensure consistency, readability, and maintainability.

## 1. Structure & Organization

The Makefile must be organized into clear, labeled sections using `##@ <Section Name>` comments. This allows the `make help` command to group targets logically.

### Required Sections (in order):
1.  **General**: Default targets and help.
2.  **Setup & Installation**: Initial project setup and environment checks.
3.  **Docker Services**: Core service checks, logs, and lifecycle (`up`, `down`, `logs`, `ps`).
4.  **Database**: Core database operations (`migrate`, `reset`, `shell`).
5.  **Seed**: Data seeding scripts.
6.  **B2B Demos**: End-to-end demo setup flows for specific use cases.
7.  **Frontend**: Local development commands for web portals.
8.  **Development**: Helper commands for backend-only dev, shells, etc.
9.  **Testing**: All test runners (`test-api`, `test-ui`, scoped suites, coverage).
10. **Performance**: Load testing targets.
11. **Security (SAST/DAST)**: Security scanning targets.
12. **Stripe**: Payment gateway helpers.

## 2. Naming Conventions & Scope Definition

Targets must use a **Category-Action-Scope** naming pattern where possible. The name should explicitly reveal *what* is being acted upon and *how*.

**Pattern:** `[category]-[action]-[scope]`

| Category | Prefix | Scope Requirement | Example | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Database** | `db-` | **Validation**: Target must effect DB state only. | `db-reset-clean` | "db" (category) + "reset" (action) + "clean" (scope: no seeds/services). |
| **Migrations** | `*-migrate` | **Implicit**: Scope is usually product-based. | `b2b-migrate` | "b2b" (scope) + "migrate" (action). |
| **Seeding** | `*-seed-*` | **Explicit**: Must specify what is being seeded. | `b2b-seed-roles` | "b2b" (category) + "seed" (action) + "roles" (scope). |
| **Demo Setup** | `demo-setup-` | **Explicit**: Must specify use case. | `demo-setup-bank` | "demo" (category) + "setup" (action) + "bank" (scope). |
| **Manual Demo** | `b2b-demo-` | **Explicit**: Must specify use case. | `b2b-demo-bank` | "b2b-demo" (category) + "bank" (scope). |
| **Testing** | `test-` | **Explicit**: Must specify type and scope. | `test-b2b-bank-full` | "test" (category) + "b2b-bank" (scope) + "full" (variant). |
| **Frontend** | `web-` | **Explicit**: Must specify app. | `web-b2b` | "web" (category) + "b2b" (scope). |
| **Security** | `sast-`/`dast-` | **Explicit**: Must specify tool or target. | `sast-scan-python` | "sast-scan" (category/action) + "python" (scope). |

### Ambiguous Names to Avoid
- `setup`: Too vague. Use `setup-project` or `demo-setup-bank`.
- `test`: Acceptable as a meta-target, but specific tests must be scoped (e.g., `test-api`).
- `reset`: Prefer `db-reset` or `reset-all` to distinguish scope.

## 3. Core Principles

### A. The "Clean Reset" Pattern
Database resets should be atomic and predictable.
- **`db-reset-clean`**: The single source of truth for resetting the DB. It must:
    1. Drop the database.
    2. Create the database.
    3. Run schema migrations (`migrate-only`).
    4. Setup auth permissions (`db-setup-auth`).
    5. **NEVER** start application services or seed data.

### B. Setup Dependencies
Targets that require the backend API to be running (like seeding) must ensure services are up:
```makefile
demo-setup-bank:
    @$(MAKE) db-reset-clean
    @docker-compose up -d ... # Start Backend
    @sleep 5                  # Wait for health
    @$(MAKE) seed-all ...     # Run Seeds
```

### C. Output Formatting
Use standard colors for output to improve readability:
- `$(BLUE)`: Information/Heading (e.g., "Starting backend services...")
- `$(GREEN)`: Success/Completion (e.g., "✓ Database reset complete")
- `$(YELLOW)`: Warnings/Prompts (e.g., "⚠ This will delete all data!")
- `$(NC)`: No Color (Reset)

### D. Verification
Complex flows (like demos) should verify their result:
```makefile
b2b-demo-bank:
    @$(MAKE) demo-setup-bank
    @$(MAKE) verify-seed  <-- Critical step
    @echo "Instructions..."
```

## 4. Documentation
Every target must have a help string following the pattern:
```makefile
target-name: ## Description of what this target does
```
These descriptions are automatically parsed by `make help`.
