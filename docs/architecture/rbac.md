# RBAC System - Usage Examples

Quick reference for using the RBAC system in your endpoints.

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
    get_accessible_farmers_query,
    can_access_farmer,
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

@router.get("/farmers")
async def list_farmers(
    current_user: dict = require_permission('farmers', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Only users with 'farmers:read' permission can access"""
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

@router.get("/farmers/{id}")
async def get_farmer(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Manual permission check
    if not await has_permission(current_user['id'], 'farmers', 'read', db):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Your code
    ...
```

---

## 📊 Scoped Queries (Hierarchical Access)

### Get Scoped Farmers

```python
from app.rbac import get_accessible_farmers_query

@router.get("/farmers")
async def list_farmers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get query scoped to user's access level
    query = await get_accessible_farmers_query(current_user['id'], db)
    
    # Execute query
    result = await db.execute(query)
    farmers = result.scalars().all()
    
    return farmers
```

### Check Single Farmer Access

```python
from app.rbac import can_access_farmer

@router.get("/farmers/{id}")
async def get_farmer(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if user can access this specific farmer
    if not await can_access_farmer(current_user['id'], id, db):
        raise HTTPException(status_code=404, detail="Farmer not found")
    
    farmer = await db.get(Farmer, id)
    return farmer
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
    #   "total_farmers": 25,   # Accessible farmers
    #   "my_farmers": 10       # Own farmers
    # }
```

---

## 🎯 Complete Example: Farmers Endpoint

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.rbac import require_permission, get_accessible_farmers_query, can_access_farmer
from app.models.rbac import Farmer
from pydantic import BaseModel

router = APIRouter()

class FarmerCreate(BaseModel):
    name: str
    email: str
    phone: str
    address: str

@router.get("/farmers")
async def list_farmers(
    current_user: dict = require_permission('farmers', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List all farmers user can access (scoped)"""
    query = await get_accessible_farmers_query(current_user['id'], db)
    result = await db.execute(query)
    farmers = result.scalars().all()
    return farmers

@router.post("/farmers")
async def create_farmer(
    farmer_data: FarmerCreate,
    current_user: dict = require_permission('farmers', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new farmer (permission required)"""
    farmer = Farmer(
        tenant_id=current_user['tenant_id'],
        name=farmer_data.name,
        email=farmer_data.email,
        phone=farmer_data.phone,
        address=farmer_data.address,
        created_by=current_user['id']  # Track ownership
    )
    db.add(farmer)
    await db.commit()
    await db.refresh(farmer)
    return farmer

@router.get("/farmers/{id}")
async def get_farmer(
    id: int,
    current_user: dict = require_permission('farmers', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """Get a farmer (with scope check)"""
    # Check if user can access this farmer
    if not await can_access_farmer(current_user['id'], id, db):
        raise HTTPException(status_code=404, detail="Farmer not found")
    
    farmer = await db.get(Farmer, id)
    return farmer

@router.delete("/farmers/{id}")
async def delete_farmer(
    id: int,
    current_user: dict = require_permission('farmers', 'delete'),
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
- `farmers` - Farmer management
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
has_permission(user_id, 'farmers', 'read', db)   # Can view farmers
has_permission(user_id, 'users', 'write', db)    # Can create/edit users
has_permission(user_id, 'roles', 'write', db)    # Can manage roles
```

---

## 📋 Role Access Summary

| Role | Dashboard | Users | Roles | Farmers |
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
- **Field Manager** (`field_manager`): Can manage agents and farmers.
- **Field Agent** (`field_agent`): Can only access assigned farmers.

### How to Add New Domain Roles
To introduce a new domain role (e.g., "Auditor"):

1.  **Define Resources**: Add 'audits' to `resources` table.
2.  **Update Seeder**: Modify `seed_tenant_roles` function in migration:
    ```sql
    -- Create Role
    INSERT INTO roles (name, ...) VALUES ('auditor', ...);
    -- Assign Permissions
    INSERT INTO role_permissions ... VALUES (v_auditor_id, v_audits_id, v_read_id);
    ```
3.  **Apply**: The new role will be created for all *new* tenants. Run a migration script to backfill *existing* tenants.

