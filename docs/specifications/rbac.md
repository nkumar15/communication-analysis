# SPEC-03: Role-Based Access Control (RBAC)

**Status**: Active / Implemented
**Last Updated**: 2025-12-11

## Overview

The Authorization system controls user access to resources based on:
1. **Tenant Role** - What actions they CAN perform (permissions)
2. **Team Membership** - Which data they can ACCESS (scope)

---

## 1. Role Definitions

### 1.1 Tenant Roles (Global)

| Role | Display Name | Description | Team Data Access |
|------|--------------|-------------|------------------|
| `owner` | **Owner** | Total control, billing, security, oversight. | ✅ ALL teams |
| `admin` | **Admin** | Management without billing/deletion. | ❌ Requires membership |
| `member` | **Member** | Standard operational access. | ❌ Requires membership |
| `viewer` | **Viewer** | Read-only access. | ❌ Requires membership |

> [!IMPORTANT]
> **Governance**: Only `owner` can see ALL team data. All other roles require team membership to access team-scoped data (projects, tasks, comments).

### 1.2 Team Scope Levels (Contextual)

| Level | Description | Capabilities |
|-------|-------------|--------------|
| `team_manager` | Manages team. | Invite/remove members, update settings. |
| `team_member` | Standard participant. | Access team data, write tasks/comments. |
| `team_viewer` | Observer. | Read-only access to team data. |

### 1.3 Default Roles (Least Privilege)

| Context | Default |
|---------|---------|
| New User Invitation | `member` tenant role |
| Team Assignment | `team_member` scope level |

---

## 2. Permission Matrix

### 2.1 Administration & System

| Resource | Action | Owner | Admin | Member | Viewer |
|----------|--------|:-----:|:-----:|:------:|:------:|
| **Users** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `invite` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ❌ | ❌ | ❌ |
| **Teams** | `write` | ✅ | ✅ | ❌ | ❌ |
| **Billing** | `manage` | ✅ | ❌ | ❌ | ❌ |
| **Security** | `manage` | ✅ | ❌ | ❌ | ❌ |
| **Audit Logs** | `read` | ✅ | ✅ | ❌ | ❌ |

### 2.2 Domain Features (Task Management)

*Seeded via `seed_domain_data.py`*

| Resource | Action | Owner | Admin | Member | Viewer |
|----------|--------|:-----:|:-----:|:------:|:------:|
| **Projects** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |
| **Tasks** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ✅ | ❌ |
| **Comments** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ✅ | ❌ |

---

## 3. Scope & Data Access

```
┌─────────────────────────────────────────────────────────┐
│ PERMISSION (Tenant Role)  │ SCOPE (Team Membership)     │
│ ─────────────────────────  │ ─────────────────────────── │
│ CAN I do this action?      │ ON WHICH data can I do it?  │
└─────────────────────────────────────────────────────────┘
```

| Role | Scope |
|------|-------|
| `owner` | All data (oversight responsibility) |
| `admin/member/viewer` | Only data in joined teams |

---

## 4. Implementation

### Storage
- `b2b.role_templates` → JSON permission templates
- `b2b.roles` → Tenant-specific roles (copied from templates)
- `b2b.role_permissions` → Role-to-resource-action mappings
- `b2b.team_members.team_role` → Team scope level (string)

### Enforcement
```python
# Permission check (can do X?)
await has_permission(user_id, 'projects', 'write', db)

# Scope check (on which data?)
team_ids = await get_user_team_ids(user_id, db)
```

> [!NOTE]
> The system checks `role_permissions` table, NOT role names.
> This allows role names to change while permissions remain stable.
