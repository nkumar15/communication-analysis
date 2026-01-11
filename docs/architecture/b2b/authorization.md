# Authorization & RBAC Architecture

**Audience:** Backend Developers  
**Last Updated:** 2026-01-11

This document details the **3-Layer Role-Based Access Control (RBAC)** system implementation, including the design philosophy, database schema, permission resolution, and implementation patterns.

For **Authentication**, see [Authentication Architecture](./authentication.md).
For **RBAC Concepts**, see [RBAC Concepts Guide](../../guides/b2b-rbac-concepts.md).

---

## 📋 Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [The 3-Layer Model](#the-3-layer-model)
3. [Database Schema](#database-schema)
4. [Permission Resolution](#permission-resolution)
5. [Implementation Patterns](#implementation-patterns)
6. [Endpoint Protection](#endpoint-protection)
7. [Configuration Architecture](#configuration-architecture)

---

## 🎯 Design Philosophy

### Core Principle

> **Separate WHY the user exists from WHAT the user can do**

The system distinguishes between:
- **Identity existence** (can they log in?)
- **Business authority** (what can they do?)
- **Data scope** (which data can they see?)

### The 3 Questions

| Question | Layer | Answer |
|----------|-------|--------|
| "Is this user allowed to use the system at all?" | System Role | Yes/No |
| "What business function do they perform?" | Tenant Role | Actions allowed |
| "Which data are they allowed to see?" | Team | Data scope |

---

## 🏗️ The 3-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: SYSTEM ROLE                                       │
│  ─────────────────────                                      │
│  • Cardinality: Exactly ONE per user (required)             │
│  • Values: owner, admin, member, viewer                     │
│  • Stored: b2b.users.role_id → b2b.roles (is_system=true)   │
│  • Purpose: Platform access, login, admin console           │
│  • Rule: Does NOT grant business data access                │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: TENANT ROLE                                       │
│  ─────────────────────                                      │
│  • Cardinality: 0..N per user (optional)                    │
│  • Values: surveillance_chief, regional_director, analyst   │
│  • Stored: b2b.user_tenant_roles (future) or role_id        │
│  • Purpose: Business action authority (WHAT)                │
│  • Rule: Does NOT define data scope                         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: TEAM MEMBERSHIP                                   │
│  ─────────────────────                                      │
│  • Cardinality: 0..N per user (optional)                    │
│  • Values: APAC, SG Desk, India, Special Investigations     │
│  • Stored: b2b.team_members (user_id, team_id, team_role)   │
│  • Purpose: Data scope (WHERE)                              │
│  • Rule: No team = no data access                           │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Controls | Does NOT Control |
|-------|----------|------------------|
| **System Role** | Login, platform UI, admin console, billing | Business data access |
| **Tenant Role** | Resource permissions, actions | Data scope |
| **Team** | Data visibility, team-specific operations | Global permissions |

---

## 💾 Database Schema

### Core Tables

```sql
-- Users with System Role assignment
CREATE TABLE b2b.users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    email VARCHAR(255) NOT NULL,
    role_id UUID REFERENCES b2b.roles(id),  -- System or Tenant role
    firebase_uid VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(tenant_id, email)
);

-- Roles (System + Tenant roles)
CREATE TABLE b2b.roles (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    is_system_role BOOLEAN DEFAULT FALSE,  -- true = owner/admin/member/viewer
    is_active BOOLEAN DEFAULT TRUE,
    permissions JSONB,
    UNIQUE(tenant_id, name)
);

-- Team Memberships with Team Role
CREATE TABLE b2b.team_members (
    id UUID PRIMARY KEY,
    team_id UUID REFERENCES b2b.teams(id),
    user_id UUID REFERENCES b2b.users(id),
    team_role VARCHAR(50) NOT NULL DEFAULT 'team_contributor',
    team_role_id UUID REFERENCES b2b.team_role_definitions(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- Team Role Definitions
CREATE TABLE b2b.team_role_definitions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    permissions JSONB,
    is_system BOOLEAN DEFAULT FALSE,
    UNIQUE(tenant_id, name)
);
```

### Role Categories

| is_system_role | Role Type | Examples |
|----------------|-----------|----------|
| TRUE | System Role | owner, admin, member, viewer |
| FALSE | Tenant Role | surveillance_chief, regional_director |

### Data Flow

```
SEED PHASE:
    YAML files → role_templates (global blueprints)

TENANT CREATION:
    role_templates → roles (per-tenant instances)
    seed_tenant_roles() creates system + tenant roles

USER INVITATION:
    roles.id → users.role_id (user gets ONE role)
    teams.id → team_members (user assigned to teams)
```

---

## 🔐 Permission Resolution

### Evaluation Algorithm

```python
async def can_access(
    user: User,
    resource: str,
    action: str,
    data_team_id: UUID | None = None
) -> bool:
    """
    3-Layer Permission Check
    
    Layer 1: System Role (can login?)
    Layer 2: Tenant Role (action allowed?)
    Layer 3: Team (data scope?)
    """
    
    # LAYER 1: System Role Check
    if not user.role or not user.role.is_active:
        return False  # No role = no access
    
    # Admin bypass for platform operations only
    if user.role.is_system_role and user.role.name in ('owner', 'admin'):
        if is_platform_resource(resource):
            return True
    
    # LAYER 2: Tenant Role Permission Check
    role_permissions = user.role.permissions or []
    has_permission = any(
        p['resource'] == resource and action in p['actions']
        for p in role_permissions
    )
    
    if not has_permission:
        return False
    
    # LAYER 3: Team Scope Check (for business data)
    if is_business_resource(resource) and data_team_id:
        team_membership = await get_team_membership(user.id, data_team_id)
        if not team_membership:
            return False
    
    return True
```

### Resolution Flow Diagram

```
Request: "Can User X approve investigation in SG Desk?"
    │
    ▼
┌─────────────────────────────────────────┐
│ LAYER 1: SYSTEM ROLE                    │
│ Does user have valid system role?       │
│ → Yes (member)                          │
└─────────────────────────────────────────┘
    │ PASS
    ▼
┌─────────────────────────────────────────┐
│ LAYER 2: TENANT ROLE                    │
│ Does role have investigations:approve?  │
│ → Yes (surveillance_chief)              │
└─────────────────────────────────────────┘
    │ PASS
    ▼
┌─────────────────────────────────────────┐
│ LAYER 3: TEAM SCOPE                     │
│ Is user member of SG Desk team?         │
│ → Yes (surveillance_lead role)          │
└─────────────────────────────────────────┘
    │ PASS
    ▼
✅ ACCESS GRANTED
```

---

## 🛠️ Implementation Patterns

### 1. System Role Check (Login Guard)

```python
# middleware/auth.py
async def require_login(user: User) -> bool:
    """Layer 1: Can user log in?"""
    if not user or not user.role:
        return False
    return user.role.is_active
```

### 2. Admin Check (Platform Operations)

```python
async def require_admin(user: User) -> bool:
    """Check if user can perform admin operations"""
    if not user.role or not user.role.is_system_role:
        return False
    return user.role.name in ('owner', 'admin')
```

### 3. Permission Check (Business Actions)

```python
async def check_permission(
    user: User, 
    resource: str, 
    action: str,
    db: AsyncSession
) -> bool:
    """Layer 2: Does user have permission for action?"""
    role = await get_user_role(db, user.id)
    if not role or not role.permissions:
        return False
    
    return any(
        p.get('resource') == resource and action in p.get('actions', [])
        for p in role.permissions
    )
```

### 4. Team Scope Check (Data Access)

```python
async def check_team_access(
    user_id: UUID,
    team_id: UUID,
    db: AsyncSession
) -> bool:
    """Layer 3: Is user member of this team?"""
    result = await db.execute(
        select(TeamMember)
        .where(TeamMember.user_id == user_id)
        .where(TeamMember.team_id == team_id)
    )
    return result.scalar_one_or_none() is not None
```

---

## 🔒 Endpoint Protection

### FastAPI Dependency Pattern

```python
from fastapi import Depends, HTTPException, status

async def require_permission(
    resource: str,
    action: str
):
    """Decorator factory for permission checks"""
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not await check_permission(current_user, resource, action, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}"
            )
        return current_user
    return Depends(dependency)

# Usage
@router.post("/investigations/{investigation_id}/approve")
async def approve_investigation(
    investigation_id: UUID,
    user: User = require_permission("investigations", "approve"),
    db: AsyncSession = Depends(get_db)
):
    # Check team scope
    investigation = await get_investigation(db, investigation_id)
    if not await check_team_access(user.id, investigation.team_id, db):
        raise HTTPException(403, "Not a member of this team")
    
    # Proceed with approval
    ...
```

### RLS Integration

```python
# For automatic data scoping via Row-Level Security
async def set_user_context(db: AsyncSession, user: User):
    """Set RLS context for automatic data filtering"""
    team_ids = await get_user_team_ids(db, user.id)
    await db.execute(text(
        f"SET LOCAL app.current_user_teams = '{{{','.join(str(t) for t in team_ids)}}}'"
    ))
```

---

## ⚙️ Configuration Architecture

### Directory Structure

```
backend/scripts/b2b/
├── core/                           # System roles (don't edit)
│   ├── actions.yaml
│   ├── saas_roles.yaml             # owner, admin, member, viewer
│   └── saas_resources.yaml         # Platform resources
│
├── domain/                         # Production: Tenant roles
│   ├── resources.yaml              # Business resources
│   ├── tenant_roles.yaml           # surveillance_chief, etc.
│   └── team_roles.yaml             # Team-specific roles
│
├── use_cases/                      # Demo templates
│   ├── bank_surveillance/
│   │   ├── tenant_roles.yaml       # Business tenant roles
│   │   ├── team_roles.yaml         # Team roles
│   │   └── README.md
│   └── marketing_agency/
```

### Seeding Process

```bash
# Development: Load use case
USE_CASE=bank_surveillance make b2b-seed-roles

# Production: Load domain
make b2b-seed-roles
```

### Role Template Flow

```
YAML (role_templates) 
    → role_templates table (global)
        → roles table (per-tenant)
            → users.role_id (assignment)
```

---

## 📊 Default User Behavior

### User with Only System Role (member)

| Capability | Allowed? |
|------------|:--------:|
| Login | ✅ |
| Dashboard shell | ✅ |
| Profile page | ✅ |
| Notifications | ✅ |
| Business data | ❌ |
| Team screens | ❌ |
| Write actions | ❌ |

### UI States

| User State | Expected UI |
|------------|-------------|
| No tenant role | "No access assigned" |
| Tenant role, no team | "Assign team to activate" |
| Team, no role | "Role required" |
| viewer role | Read-only (hide write buttons) |
| admin role | Show admin console |

---

## 📖 See Also

- [RBAC Concepts Guide](../../guides/b2b-rbac-concepts.md) - Overview and golden rules
- [RBAC Plugin Architecture](./rbac-plugins.md) - Enterprise extensions (hierarchy, geography, classification)
- [Bank Surveillance Use Case](../../../backend/scripts/b2b/use_cases/bank_surveillance/README.md) - Enterprise example
