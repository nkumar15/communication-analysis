# Authorization & RBAC Architecture

**Audience:** Backend Developers

This document details the **Role-Based Access Control (RBAC)** system, explaining how to protect endpoints, check permissions, and manage roles using the B2B framework.

For **Authentication**, see [Authentication Architecture](./authentication.md).

---

## 📚 Core Components

### 1. Database Schema (`b2b` schema)
*   **`b2b.roles`**: Tenant-specific roles (e.g., Owner, Admin).
*   **`b2b.role_permissions`**: Mapping of Roles to Permissions (`resource` + `action`).
*   **`b2b.role_templates`**: Global templates used to seed roles for new tenants.

### 2. Services
*   **`PermissionChecker`**: Core logic for verifying `user_id + resource + action`.
*   **`RoleTemplateService`**: Manages seeding and updating roles from templates.
*   **`ScopeChecker`**: specialized logic for hierarchical data access (Team vs Tenant scope).
    *   **`is_team_manager(user_id, team_id)`**: Returns true if user is a manager of the specific team.
    *   **`can_manage_team(user_id, team_id)`**: Returns true if user is a team manager OR has global `teams:write` permission.

---

## 🔐 Protecting Endpoints

Use the decorators from `services.b2b.rbac.decorators` to secure API routes.

### 1. Require Permission (Preferred)
Checks if the user's role has the specific capability.

```python
from services.b2b.rbac.decorators import require_permission

@router.get("/projects")
@require_permission('projects', 'read')
async def list_projects(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Only users with 'projects:read' permission can access.
    Owner/Admin have this by default.
    """
    pass
```

### 2. Require Role (Specific)
Checks for a specific named role. Use sparingly; prefer permissions for flexibility.

```python
from services.b2b.rbac.decorators import require_role

@router.post("/invite")
@require_role('admin', 'owner', 'team_manager')
async def invite_user(
    email: str,
    # ...
):
    """Only admins or team managers can invite"""
    pass
```

---

## 🔍 Data Scoping (RLS vs Application)

**1. Database Level (RLS)**
*   **Mechanism**: `SET LOCAL app.current_tenant_id`
*   **Effect**: Users strictly cannot see data from other tenants.

**2. Application Level (Team/User Scope)**
*   **Mechanism**: `ScopeChecker` service.
*   **Effect**: Filters data *within* the tenant (e.g., A user only sees their specific Team's tasks).

```python
from services.b2b.rbac.scope_checker import get_accessible_user_ids

# Example: Get users I am allowed to see
accessible_ids = await get_accessible_user_ids(user_id, db)
query = select(UserModel).where(UserModel.id.in_(accessible_ids))
```

---

## 🏗️ Role Management

### Role Templates (Seeding)
New tenants are automatically seeded with roles defined in `b2b.role_templates`.

*   **Standard Roles**: `owner`, `admin`, `viewer`.
*   **Team Roles**: `team_manager`, `team_member`.

### Adding New Domain Roles
To add a domain-specific role (e.g., "Auditor"):

1.  **Seed Resource**: Add resource to `seed_domain_data.py`.
2.  **Seed Template**: Add/Update template in `seed_domain_data.py`.
3.  **Run Script**: `python -m scripts.b2b.seed_domain_data`.

```python
# scripts/b2b/seed_domain_data.py
Resource(name='audits', display_name='Audits', ...)
```
