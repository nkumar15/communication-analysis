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

### Adding New Permissions
To support new features or domains:

#### 1. Add Resource
Add the new resource definition to `scripts/b2b/seed_domain_data.py`:
```python
dom_resources = [
    Resource(name='invoices', display_name='Invoices', ...)
]
```

#### 2. Update Tenant Roles (Global)
Update `role_templates` in the seed script to include permissions for the new resource.
```python
# For 'admin' template
admin.permissions.append({"resource": "invoices", "actions": ["read", "write"]})
```

#### 3. Update Team Roles (Contextual)
Update `TeamRoleDefinition` seeding in `seed_domain_data.py`.
```python
# For 'team_contributor'
contributor.permissions.append({"resource": "invoices", "actions": ["read"]})
```
