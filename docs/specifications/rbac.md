# SPEC-03: Role-Based Access Control (RBAC)

**Status**: Active / Implemented  
**Last Updated**: 2025-12-11

---

## Overview

The authorization system uses a **two-dimensional access control** model:

| Dimension | Question | Controlled By |
|-----------|----------|---------------|
| **Permission** | "Can I do this action?" | Tenant Role |
| **Scope** | "On which data?" | Team Membership |

---

## 1. Tenant Roles vs Team Scope Levels

This is the most important distinction in the RBAC system.

### 1.1 Tenant Roles (Global Permissions)

**Purpose**: Define what ACTIONS a user can perform across the entire tenant.

| Role | Description | Key Permissions | Team Data Access |
|------|-------------|-----------------|------------------|
| `owner` | Account owner with total control | Billing, security, delete users | ✅ ALL teams |
| `admin` | Manager without billing access | Invite users, manage teams | ❌ Requires membership |
| `member` | Standard operational access | Tasks, comments | ❌ Requires membership |
| `viewer` | Read-only access | View only | ❌ Requires membership |

**Storage**: `b2b.roles` table (per-tenant) + `b2b.role_permissions` (permission grants)

**Example**: A user with `admin` role CAN manage teams but CANNOT see billing.

### 1.2 Team Scope Levels (Contextual Access)

**Purpose**: Define a user's RELATIONSHIP within a specific team.

| Scope Level | Description | Within-Team Capabilities |
|-------------|-------------|-------------------------|
| `team_manager` | Team lead | Invite/remove team members, update team settings |
| `team_member` | Participant | Access team's projects/tasks/comments |
| `team_viewer` | Observer | Read-only access to team's data |

**Storage**: `team_members.team_role` column (string value)

**Example**: A user can be `team_manager` in Team A but `team_viewer` in Team B.

### 1.3 How They Work Together

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER ACCESS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   TENANT ROLE         +         TEAM MEMBERSHIP                 │
│   (what you CAN do)             (where you can do it)           │
│                                                                 │
│   ┌─────────────┐              ┌─────────────────────┐          │
│   │   member    │      +       │ Team A: team_member │          │
│   │             │              │ Team B: team_viewer │          │
│   └─────────────┘              └─────────────────────┘          │
│                                                                 │
│   Result: Can write tasks in Team A, read-only in Team B       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Governance Rule**: Only `owner` role bypasses team membership requirements.
> All other roles (admin, member, viewer) can only access data in teams they belong to.

---

## 2. Permission Matrix

### 2.1 Core (Administration)

| Resource | Action | Owner | Admin | Member | Viewer |
|----------|--------|:-----:|:-----:|:------:|:------:|
| **Users** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `invite` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ❌ | ❌ | ❌ |
| **Teams** | `write` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |
| **Billing** | `manage` | ✅ | ❌ | ❌ | ❌ |
| **Audit Logs** | `read` | ✅ | ✅ | ❌ | ❌ |

### 2.2 Domain (Task Management)

*Seeded via `seed_domain_data.py`*

| Resource | Action | Owner | Admin | Member | Viewer |
|----------|--------|:-----:|:-----:|:------:|:------:|
| **Projects** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |
| **Tasks** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ✅ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |
| **Comments** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ✅ | ❌ |
| | `delete` | ✅ | ✅ | ✅ | ❌ |

---

## 3. Default Role Assignments

| Context | Default Value | Changeable |
|---------|---------------|------------|
| New User Invitation | `member` | Yes, by inviter |
| Team Assignment | `team_member` | Yes, by team manager |

---

## 4. Implementation Details

### Storage Architecture

| Table | Purpose | Scope |
|-------|---------|-------|
| `b2b.role_templates` | JSON permission blueprints | Global |
| `b2b.roles` | Tenant-specific roles | Per-tenant |
| `b2b.role_permissions` | Relational permission grants | Per-tenant-role |
| `b2b.resources` | Available resources | Global |
| `b2b.actions` | Available actions | Global |
| `b2b.team_members.team_role` | Team scope level | Per-team-membership |

### Enforcement

```python
# 1. Permission check (can user do this action?)
await has_permission(user_id, 'projects', 'write', db)

# 2. Scope check (which teams can user access?)
team_ids = await get_user_team_ids(user_id, db)
```

> [!NOTE]
> The system checks `role_permissions` table, NOT role names.
> This allows role names to change while permissions remain stable.

---

## 5. Creating New Roles

The current design supports creating new roles. Here's the procedure:

### 5.1 Add a New Tenant Role

#### Step 1: Add Role Template (Migration)

Edit `migrations/004_b2b_rbac.sql`:

```sql
INSERT INTO b2b.role_templates (name, display_name, description, is_system_role, is_default, permissions)
VALUES (
    'supervisor',
    'Supervisor',
    'Can manage users but not delete them',
    TRUE,
    TRUE,
    '[
        {"resource": "dashboard", "actions": ["read"]},
        {"resource": "users", "actions": ["read", "write"]},
        {"resource": "teams", "actions": ["read"]}
    ]'::jsonb
);
```

#### Step 2: Add Domain Permissions (Seed Script)

Edit `scripts/b2b/seed_domain_data.py`:

```python
# Update supervisor role
result = await db.execute(select(RoleTemplate).where(RoleTemplate.name == 'supervisor'))
supervisor = result.scalar_one_or_none()
if supervisor:
    domain_perms = [
        {"resource": "projects", "actions": ["read", "write"]},
        {"resource": "tasks", "actions": ["read", "write"]},
    ]
    for perm in domain_perms:
        if perm not in supervisor.permissions:
            supervisor.permissions.append(perm)
    flag_modified(supervisor, 'permissions')
    await db.commit()
```

#### Step 3: Re-run Migrations and Seed

```bash
make db-reset       # Or apply migration
make b2b-seed-roles-templates
```

### 5.2 Add a New Team Scope Level

Team scope levels are simpler - just strings stored in `team_members.team_role`.

#### Step 1: Update the Enum/Validation (Optional)

If you have validation, add the new level:

```python
# In models or constants
TEAM_ROLES = ['team_manager', 'team_member', 'team_viewer', 'team_lead']  # Add new
```

#### Step 2: Update Scope Checker

Edit `services/b2b/rbac/scope_checker.py` to handle the new level:

```python
async def can_manage_team(user_id: UUID, team_id: UUID, db) -> bool:
    # Add team_lead to allowed list
    if team_role in ('team_manager', 'team_lead'):
        return True
```

### 5.3 Add a New Resource

#### Step 1: Add to Seed Script

Edit `scripts/b2b/seed_domain_data.py`:

```python
domain_resources = [
    Resource(name='invoices', display_name='Invoices', category='Domain', description='Invoice management'),
    # ... existing resources
]
```

#### Step 2: Update Role Templates

Add permissions for the new resource to relevant roles in the same script.

---

## 6. Quick Reference

| Concept | Storage | Enforcement |
|---------|---------|-------------|
| Tenant Role | `b2b.users.role_id` → `b2b.roles` | `permission_checker.py` |
| Team Scope | `b2b.team_members.team_role` | `scope_checker.py` |
| Domain Permissions | `b2b.role_permissions` | Joined query |
