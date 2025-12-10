# Authorization & RBAC Architecture

**Audience:** Backend Developers

This document details the **Role-Based Access Control (RBAC)** system, explaining how to protect endpoints, check permissions, and manage roles.
For **Authentication** (Login/Identity), see [Authentication Architecture](./authentication.md).
For **Data Isolation** (RLS), see [Multi-Tenant Isolation](./multi-tenant-isolation.md).

---

## 📚 Import

```python
from app.rbac import (
    # Decorators
    require_permission,
    require_role,
    
    # Permission checkers
    has_permission,
    get_user_permissions,
    
    # Scope helpers
    get_dashboard_stats
)
```

---

## 🔐 Protecting Endpoints

### Using Permission Decorator

```python
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.rbac import require_permission

router = APIRouter()

@router.get("/projects")
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Only users with 'projects:read' permission can access"""
    # ... your code
```

### Using Role Decorator

```python
@router.post("/users/invite")
async def invite_user(
    email: str,
    current_user: dict = require_role('admin', 'field_manager'),
    db: AsyncSession = Depends(get_db)
):
    """Only admin and field_manager can invite users"""
    # ... your code
```

---

## 🔍 Manual Permission Checks

```python
from app.rbac import has_permission

@router.get("/projects/{id}")
async def get_project(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Manual permission check
    if not await has_permission(current_user['id'], 'projects', 'read', db):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Your code
    ...
```

---

## 📊 Scoped Queries (Hierarchical Access)

### Get Scoped Projects

```python
from app.rbac import get_accessible_projects_query

@router.get("/projects")
async def list_projects(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get query scoped to user's access level
    query = await get_accessible_projects_query(current_user['id'], db)
    
    # Execute query
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return projects
```

### Check Single Project Access

```python
from app.rbac import can_access_project

@router.get("/projects/{id}")
async def get_project(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if user can access this specific project
    if not await can_access_project(current_user['id'], id, db):
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await db.get(Project, id)
    return project
```

### Get Scoped Statistics

```python
from app.rbac import get_dashboard_stats

@router.get("/dashboard/stats")
async def dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get stats scoped to user's access level
    stats = await get_dashboard_stats(current_user['id'], db)
    
    return stats
    # Returns: {
    #   "total_users": 5,      # Users in hierarchy
    #   "total_projects": 25,   # Accessible projects
    #   "my_projects": 10       # Own projects
    # }
```

---

## 🎯 Complete Example: Projects Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.rbac import require_permission, get_accessible_projects_query, can_access_project
from app.models.rbac import Project
from pydantic import BaseModel

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    email: str
    phone: str
    address: str

@router.get("/projects")
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List all projects user can access (scoped)"""
    query = await get_accessible_projects_query(current_user['id'], db)
    result = await db.execute(query)
    projects = result.scalars().all()
    return projects

@router.post("/projects")
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = require_permission('projects', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new project (permission required)"""
    project = Project(
        tenant_id=current_user['tenant_id'],
        name=project_data.name,
        email=project_data.email,
        phone=project_data.phone,
        address=farmer_data.address,
        created_by=current_user['id']  # Track ownership
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/projects/{id}")
async def get_project(
    id: int,
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Get a project (with scope check)"""
    # Check if user can access this project
    if not await can_access_project(current_user['id'], id, db):
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = await db.get(Project, id)
    return project

@router.delete("/projects/{id}")
async def delete_project(
    id: int,
    current_user: dict = require_permission('projects', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """Delete a farmer (permission + scope check)"""
    # Check access
    if not await can_access_farmer(current_user['id'], id, db):
        raise HTTPException(status_code=404, detail="Farmer not found")
    
    farmer = await db.get(Farmer, id)
    await db.delete(farmer)
    await db.commit()
    return {"message": "Farmer deleted"}
```

---

## 🔑 Permission Strings

### Resources
- `dashboard` - Statistics and overview
- `users` - User management
- `roles` - Role management
- `projects` - Project management
- `tasks` - Task management
- `comments` - Commenting system

### Actions
- `read` - View/list data
- `write` - Create/edit data
- `delete` - Delete data
- `invite` - Invite users

### Examples
```python
has_permission(user_id, 'users', 'write', db)    # Can create/edit users
has_permission(user_id, 'roles', 'write', db)    # Can manage roles
```

---

## 📋 Role Access Summary

| Role | Dashboard | Users | Roles | Projects |
|------|-----------|-------|-------|---------|
| **Admin** | ✅ All | ✅ All | ✅ Manage | ✅ All |
| **Field Manager** | ✅ Team | 📨 Invite Agents | ✅ Manage | ✅ Team |
| **Field Agent** | ❌ No Access | ❌ No Access | ❌ No Access | ✅ Own Only |

---

---

## 🏗️ Role Definition & Seeding Strategy

The system distinguishes between **Standard Roles** (SaaS infrastructure) and **Domain Roles** (Business logic).

### 1. Platform Roles (Standard)
Defined in `backend/scripts/platform/seed_system_tenant.py`.
- **Scope**: Global (Platform Tenant).
- **Roles**:
    - `platform_admin`: Super admin.
    - `support_staff`: Read-only/Support access.
    - `billing_manager`: Finance access.

### 2. B2B Tenant Roles (Standard + Domain)
Defined in PostgreSQL function `seed_tenant_roles` (Migration `015`).
This function is automatically called whenever a new tenant is created.

#### Standard Roles (Infrastructure)
Every SaaS tenant needs these:
- **Admin** (`admin`): Full access to `users`, `roles`, `dashboard`.
- **Member** (Optional): Basic access.

#### Domain Roles (Business Specific)
Specific to the application's domain (e.g., Farming, Healthcare, CRM).
- **Field Manager** (`field_manager`): Can manage agents and projects.
- **Field Agent** (`field_agent`): Can only access assigned projects.

### How to Add New Domain Roles
To introduce a new domain role (e.g., "Auditor"):

1.  **Define Resources**: Add 'projects' to `resources` table.
2.  **Update Seeder**: Modify `seed_tenant_roles` function in migration:
    ```sql
    -- Create Role
    INSERT INTO roles (name, ...) VALUES ('auditor', ...);
    -- Assign Permissions
    INSERT INTO role_permissions ... VALUES (v_auditor_id, v_audits_id, v_read_id);
    ```
3.  **Apply**: The new role will be created for all *new* tenants. Run a migration script to backfill *existing* tenants.

