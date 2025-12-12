# Test Reorganization Plan

**Objective**: Simplify the `backend/tests/e2e_api/b2b/` directory by grouping related tests and deduplicating redundant files.

## 1. Context
Currently, the `b2b` directory contains ~19 flat files. This makes it hard to navigate features (Auth vs Domain vs Onboarding).

## 2. Proposed Folder Structure

We will categorize tests into 4 semantic domains:

```text
backend/tests/e2e_api/b2b/
├── conftest.py                   # Shared fixtures (Keep at root)
├── iam/                          # Identity & Access Management
│   ├── test_auth.py
│   ├── test_mobile_auth.py
│   ├── test_impersonation.py
│   ├── test_rbac.py              # General RBAC policies
│   └── test_multi_tenant_isolation.py
├── onboarding/                   # Tenant Lifecycle
│   ├── test_activation.py        # MERGED: flow + security + errors
│   └── test_complete_e2e.py
├── organization/                 # Org Structure (Users/Teams)
│   ├── test_invitations.py
│   └── test_teams.py
├── domain/                       # Core Business Logic
│   ├── test_projects.py          # MERGED: projects + rbac_projects
│   ├── test_tasks.py
│   └── test_comments.py
└── validation/                   # Cross-cutting concerns
    └── test_audit_logs.py        # MERGED: creation + api
```

## 3. Consolidation Actions

### A. Audit Logs
- **Merge**: `test_audit_logs_api.py` ➡️ `test_audit_logs.py`
- **Rationale**: Separate files for "checking DB" vs "checking API" is unnecessary. One file should test the feature holistically.
- **Action**: Move `TestAuditLogsAPI` class into `test_audit_logs.py`.

### B. Activation / Onboarding
- **Merge**: `test_activation_flow.py` + `test_activation_security.py` + `test_activation_errors.py` ➡️ `onboarding/test_activation.py`
- **Rationale**: These split files create fragmentation. A single file covering "Happy Path", "Error Cases", and "Security Edge Cases" is easier to maintain.

### C. Projects
- **Merge**: `test_rbac_projects.py` ➡️ `domain/test_projects.py`
- **Rationale**: `test_projects.py` tests CRUD. `test_rbac_projects.py` tests "can I CRUD?". These are tightly coupled.

## 4. Execution Plan
1.  Create subdirectories (`iam`, `onboarding`, `organization`, `domain`, `validation`).
2.  Perform file moves.
3.  Perform content merges (Audit Logs, Projects, Activation).
4.  Run `pytest tests/e2e_api/b2b/` to verify imports and execution.
