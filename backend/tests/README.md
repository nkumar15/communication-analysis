# Backend Testing Guide

This directory contains the automated test suite for the Enterprise SSO backend.

## 📁 Directory Structure

The test suite is organized into two main categories: **Core Platform** and **Business Use Cases**.

```
backend/tests/
├── conftest.py             # Global fixtures (DB session, API client)
├── seed_utils.py           # Database seeding logic (loads prod YAMLs)
├── e2e_api/
│   └── b2b/
│       ├── core/           # 🌍 UNIVERSAL Platform Tests
│       │   ├── iam/        # Auth, RBAC, Roles (Platform logic)
│       │   ├── billing/    # Subscriptions, Invoices
│       │   ├── org/        # Teams, Invites, Users
│       │   └── conftest.py # Defaults to "bank_surveillance" seed
│       │
│       └── use_cases/      # 🏢 DOMAIN SPECIFIC Tests
│           ├── bank_surveillance/
│           │   ├── test_plugins.py        # Tests plugin logic
│           │   └── conftest.py            # Enforces USE_CASE=bank_surveillance
│           │
│           └── task_management/
│               ├── test_projects.py       # Tests projects/tasks
│               └── conftest.py            # Enforces USE_CASE=task_management
```

## 🧪 Testing Methodology

### 1. Seeding Strategy (The "Real World" Approach)
We do NOT use synthetic factories (e.g., `FactoryBoy`) for static data.
Instead, we perform **Integration Seeding** using the **exact same scripts** as production.

*   **Session Scope**: The database is seeded **ONCE** at the start of the test session.
*   **Production Parity**: We load roles, permissions, and resources from `backend/scripts/b2b/use_cases/`.
*   **Result**: If the seed script is broken, tests fail (good!). If config changes, tests verify it.

### 2. Core vs. Use Case Tests
*   **Core Tests (`core/`)**: Verify platform features that must work for *everyone* (e.g., "Can I login?", "Can I invite a user?", "Does billing work?"). These run against a default rich seed (Bank Surveillance).
*   **Use Case Tests (`use_cases/`)**: Verify domain-specific logic. These require specific resources (e.g., "Assessments", "Projects") that only exist in that use case.

## 🚀 Running Tests

We use `make` commands to handle environment setup.

| Command | Scope | Description |
|---------|-------|-------------|
| **`make test-b2b`** | **ALL** | **Run this before PR.** Runs Core + All Use Cases. |
| `make test-b2b-core` | Core Only | Fast run of platform features (Auth, IAM, Billing). |
| `make test-b2b-use-cases` | Use Cases | Runs specific domain tests (Bank, Task, etc). |

## ➕ How to Add a New Use Case

1.  **Define Configuration**:
    *   Create `backend/scripts/b2b/use_cases/<my_use_case>/`
    *   Add `resources.yaml`, `team_roles.yaml`, etc.

2.  **Add Test Directory**:
    *   Create `tests/e2e_api/b2b/use_cases/<my_use_case>/`

3.  **Add `conftest.py`**:
    *   Copy from `task_management/conftest.py`.
    *   Update `enforce_use_case` fixture to check for `USE_CASE=<my_use_case>`.

4.  **Register in Makefile**:
    *   Add `test-b2b-<my_use_case>` target.
    *   Add it to `test-b2b-use-cases` group.

## 🛠 Troubleshooting

*   **"Table not found"**: Ensure the `USE_CASE` env var matches the directory you are testing.
*   **"Role not found"**: Check `backend/scripts/b2b/use_cases/<case>/team_roles.yaml`.
*   **Seeding Errors**: Check `tests/seed_utils.py` logic. It mirrors `seed_rbac.py`.
