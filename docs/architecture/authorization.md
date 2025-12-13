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
*   **`b2b.team_role_definitions`**: Team-level role definitions containing a JSONB `permissions` column.

### 2. Services
*   **`PermissionChecker`**: Core logic for verifying `user_id + resource + action` (Tenant Level).
*   **`TeamRoleService`**: CRUD for team-level role definitions.
*   **`ScopeChecker`**: Specialized logic for hierarchical data access (Team vs Tenant scope).
    *   **`can_perform_action(user_id, team_id, resource, action)`**: Checks if user has permission within a specific team context (e.g., creates a task).
    *   **`can_manage_team(user_id, team_id)`**: Checks for `team_members:manage` permission.

---

## 🔐 Protecting Endpoints

Use the decorators from `services.b2b.rbac.decorators` to secure API routes.

> [!NOTE]
> **Design Decision: Dependencies vs. Wrappers**
> We use FastAPI **Dependency Factories** (via `Depends()`) instead of standard Python reference decorators for three reasons:
> 1.  **OpenAPI Integration**: Permissions automatically appear in the Swagger documentation security scheme.
> 2.  **Dependency Injection**: Dependencies automatically receive the `db` session and `current_user` without complex argument inspection.
> 3.  **Testability**: Permissions can be easily mocked using `app.dependency_overrides` during testing.

### 1. Require Permission (Preferred)
Checks if the user's role has the specific capability.

```python
from services.b2b.rbac.decorators import require_permission

@router.get("/projects")
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
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
async def invite_user(
    email: str,
    # ...
    current_user: dict = require_role('admin', 'owner', 'team_manager')
):
    """Only admins or team managers can invite"""
    pass
```

### 3. Granular Team Scope (Resource Access)
For actions within a team (e.g., creating tasks), use `can_perform_action` inside the endpoint.

```python
from services.domains.projects.scope_checker import can_perform_action

@router.post("/tasks")
async def create_task(data: TaskCreate, ...):
    project = await get_project(data.project_id)
    
    # Check if user's team role allows writing tasks
    if not await can_perform_action(user.id, project.team_id, 'tasks', 'write', user.role, db):
        raise Forbidden("Cannot create tasks in this team")
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

---

## 🚀 Extending Domain APIs (New Feature Guide)

When introducing a new domain (e.g., Human Resources), follow these steps to integrate with the B2B framework and RBAC system.

### Step 1: Create Service Structure
Create a new package under `services/domains/`:

```
services/domains/hr/
├── __init__.py
├── models.py           # Database models (RLS-enabled)
├── schemas.py          # Pydantic models
├── router.py           # FastAPI endpoints
└── service.py          # Business logic
```

### Step 2: Define Resources & Actions
Register the new domain resources in `scripts/b2b/seed_domain_data.py`:

```python
# 1. Add Resource Definition
hr_resources = [
    Resource(
        name='employees', 
        display_name='Employees', 
        category='HR', 
        description='Employee records'
    ),
    Resource(
        name='payrolls', 
        display_name='Payrolls', 
        category='HR', 
        description='Payroll processing'
    )
]

# 2. Update Default Permissions (Role Templates)
# Grant 'admin' access to new resources
admin_template.permissions.append({"resource": "employees", "actions": ["read", "write"]})
admin_template.permissions.append({"resource": "payrolls", "actions": ["read", "write"]})

# 3. Update Team Roles (if applicable)
# Be careful adding sensitive domains to general team roles
hr_manager_role.permissions.append({"resource": "employees", "actions": ["read"]})
```

### Step 3: Implement Protected Endpoints
Use the standard decorators in `services/domains/hr/router.py`.

**Tenant-Level Access (General):**
```python
from services.b2b.rbac.decorators import require_permission

@router.get("/employees")
@require_permission('employees', 'read')
async def list_employees(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await hr_service.get_all(db)
```

**Team-Level Access (Contextual):**
If the resource belongs to a team (like Projects), use explicit scope checks in `service.py`:

```python
# In service.py
async def create_payroll(user_id, team_id, data, db):
    # Verify user has permission WITHIN this specific team
    if not await scope_checker.can_perform_action(user_id, team_id, 'payrolls', 'write', db):
        raise Forbidden("Access denied for this team")
    
    # Create record...
```

### Step 4: Run Migrations
1. Run the seed script to populate `resources`, `actions`, and update `role_templates`.
2. Existing tenants will need a migration script to update their `roles` table if you want to perform a backfill (optional, as templates apply to new tenants).
