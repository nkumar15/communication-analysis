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

**Storage**: `team_members.team_role_id` → `b2b.team_role_definitions.id`.
(Note: `team_role` string is kept denormalized for quick access/legacy support, but permissions live in the definition).

**Team Management Rules**:
1. **Creation**: The user who creates a team is automatically assigned the `team_manager` role.
2. **Manager Protection**:
   * A `team_manager` CANNOT remove or change the role of another `team_manager`.
   * Only a tenant `admin` (or `owner`) can remove or demote a `team_manager`.
3. **Self-Protection**: A user cannot remove themselves from a team via the management UI (must use "Leave Team" flow).

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

**Tenant Roles (Global)**

| Resource | Action | Owner | Admin | Member | Viewer |
|----------|--------|:-----:|:-----:|:------:|:------:|
| **Projects** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |

**Team Roles (Contextual)**

| Resource | Action | Manager | Contributor | Reader |
|----------|--------|:-------:|:-----------:|:------:|
| **Projects** | `read` | ✅ | ✅ | ✅ |
| | `write` | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ❌ | ❌ |
| **Tasks** | `read` | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ |
| | `delete` | ✅ | ❌ | ❌ |
| **Comments** | `read` | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ |
| | `delete` | ✅ | ✅ | ❌ |

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
| `b2b.team_role_definitions`| JSON permission definitions | Tenant/Global |
| `b2b.team_members` | Link user to team + role def | Per-team-membership |

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

### 5.2 Add a New Team Scope Level (Team Role)

Team roles are now defined by granular permissions in the `b2b.team_role_definitions` table.

#### Step 1: Add Definition (Seed Script)

Edit `scripts/b2b/seed_domain_data.py` (or creating a new migration if adding a system-wide default):

```python
# Create or Update a team role
role = TeamRoleDefinition(
    name='team_lead',
    display_name='Team Lead',
    permissions=[
        {"resource": "projects", "actions": ["read", "write"]},
        {"resource": "tasks", "actions": ["read", "write", "delete"]},
        {"resource": "team_members", "actions": ["manage"]} # Special management perm
    ]
)
db.add(role)
```

#### Step 2: Use helper in code

You can now rely on `can_perform_action` or specific capability checks:

```python
# Check generic permission
await can_perform_action(user_id, team_id, 'tasks', 'delete', role_slug, db)

# Check management capability (mapped from 'team_members:manage')
await can_manage_team(user_id, team_id, db)
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

---

## 7. Frontend Integration

The `/auth/me` API returns permissions and teams for frontend component visibility control.

### API Response

```json
{
    "id": "...",
    "email": "user@company.com",
    "role": "member",
    "role_display_name": "Member",
    "tenant_id": "...",
    "tenant_name": "Company Inc",
    "permissions": ["projects:read", "tasks:read", "tasks:write", "comments:read"],
    "teams": [
        {"id": "...", "name": "Engineering", "team_role": "team_member"}
    ]
}
```

### useAuth Hook

```javascript
import useAuth from 'core/hooks/useAuth';

const MyComponent = () => {
    const { 
        user,
        hasPermission,  // Check resource:action
        canAccess,      // Check feature access
        getTeams,       // Get user's teams
        isTeamManager   // Check if manages any team
    } = useAuth();

    return (
        <>
            {/* Component visibility based on permission */}
            {hasPermission('users', 'invite') && <InviteButton />}
            
            {/* Feature access */}
            {canAccess('audit_logs') && <AuditLogsLink />}
            
            {/* Team-based UI */}
            {isTeamManager() && <ManageTeamButton />}
        </>
    );
};
```

### Permission Mapping

| Feature | Required Permission |
|---------|---------------------|
| Dashboard | `dashboard:read` |
| Projects | `projects:read` |
| Users | `users:read` |
| Teams | `teams:read` |
| Audit Logs | `audit_logs:read` |
| Invitations | `invitations:read` |

