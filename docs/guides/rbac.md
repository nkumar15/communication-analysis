# Role-Based Access Control (RBAC) Guide

**Audience:** Developers and System Architects

This guide explains the RBAC implementation in the SSO boilerplate, including tenant roles, team roles, and permission management.

---

## Table of Contents

1. [Overview](#overview)
2. [Role Architecture](#role-architecture)
3. [Invitation Workflows](#invitation-workflows)
4. [Permission Model](#permission-model)
5 [Best Practices](#best-practices)

---

## Overview

The system implements a **two-level role system**:

1. **Tenant Roles** - Organization-wide permissions (owner, admin, viewer)
2. **Team Roles** - Team-specific permissions (team_manager, team_member, team_viewer)

This pattern is used by GitHub, Slack, and Google Workspace for multi-tenant collaboration.

---

## Role Architecture

### Tenant Roles (Organization-Wide)

**Purpose:** Define what a user can do across the entire organization

**Examples:**
- `owner` - Full control over account, billing, and all features
- `admin` - Management capabilities (no billing/account deletion)
- `viewer` - Read-only access

**Storage:** `b2b.roles` table (per tenant)

**Assignment:** During user invitation

**Characteristics:**
- Every user has exactly ONE tenant role
- Persists across all teams
- Controls organization-level permissions (invite users, manage billing, etc.)

### Team Roles (Team-Specific)

**Purpose:** Define what a user can do within a specific team

**Examples:**
- `team_manager` - Can add/remove team members, edit team settings
- `team_member` - Active participant in team
- `team_viewer` - Read-only access to team

**Storage:** `b2b.team_members.team_role` column

**Assignment:** When adding user to a team

**Characteristics:**
- A user can have DIFFERENT roles in DIFFERENT teams
- Only applies within that team's context
- Does NOT override tenant-level permissions

---

## Invitation Workflows

### Standard Workflow

1. **Admin invites user** → Creates invitation with tenant role
2. **User receives email** → Clicks invitation link
3. **User completes SSO** → Authenticates via Firebase
4. **User joins tenant** → Account created with assigned role
5. **Optional: Auto-add to team** → If team specified, user added with team role

### Who Can Invite?

Only users with `users:invite` permission can invite new users:
- ✅ Owner
- ✅ Admin  
- ❌ Viewer (no permission)

### Enhanced Invitation (Optional Team Assignment)

When inviting a user, you can optionally:
- Select a team
- Select a team role

The user will be automatically added to that team upon accepting the invitation.

```json
{
  "email": "user@company.com",
  "role": "viewer",
  "team_id": "uuid-of-engineering-team",
  "team_role": "team_member"
}
```

**Result:**
- User created with tenant role = `viewer`
- User added to Engineering team with role = `team_member`

---

## Permission Model

### Permission Evaluation

Permissions are checked at two levels:

**1. Tenant-Level Permission:**
```python
if await has_permission(user_id, 'users', 'invite', db):
    # User can invite new users to organization
```

**2. Team-Level Permission:**
```python
if await can_manage_team(user_id, team_id, db):
    # User can manage this specific team
```

### Example Scenario

**User:** Alice  
**Tenant Role:** `admin`  
**Team Roles:**
  - Engineering: `team_manager`
  - Marketing: `team_viewer`

**Questions:**

**Q: Can Alice invite new users to the organization?**
- Check: `admin` role has `users:invite` permission?
- Answer: **YES** ✅

**Q: Can Alice add members to Engineering team?**
- Check 1: Tenant role `admin` has `teams:write`? **YES** ✅
- OR Check 2: Team role in Engineering = `team_manager`? **YES** ✅
- Answer: **YES** ✅

**Q: Can Alice add members to Marketing team?**
- Check 1: Tenant role `admin` has `teams:write`? **YES** ✅
- OR Check 2: Team role in Marketing = `team_viewer`? **NO** ❌
- Answer: **YES** ✅ (because of tenant role)

### Permission Hierarchy

**Tenant permissions > Team permissions**

If a user's tenant role grants a permission, team role cannot restrict it.

---

## Best Practices

### 1. Default Team Assignment

**Recommendation:** Auto-add new users to a default team

```python
# In invitation acceptance
default_team = await team_service.get_or_create_default_team(tenant_id)
await team_service.add_team_member(default_team.id, user.id, 'team_member')
```

### 2. Clear Role Naming

- Tenant roles: Owner, Admin, Viewer  
- Team roles: Team Manager, Team Member, Team Viewer

Prefix team roles with "Team" to avoid confusion.

### 3. Invitation Best Practices

**DO:**
- ✅ Default to lowest privilege role (viewer)
- ✅ Optionally assign to team during invitation
- ✅ Send clear invitation emails

**DON'T:**
- ❌ Allow viewers to invite users
- ❌ Default to admin role
- ❌ Skip email verification

### 4. Testing Checklist

When implementing RBAC:
- [ ] Test owner can invite all roles
- [ ] Test admin cannot invite owner
- [ ] Test viewer cannot invite anyone
- [ ] Test team manager can add to their team
- [ ] Test team viewer cannot add members
- [ ] Test auto-assignment to default team

---

## API Reference

### Invite User

```http
POST /api/b2b/invitations/invite
Content-Type: application/json
Authorization: Bearer {token}

{
  "email": "user@company.com",
  "role": "viewer",
  "team_id": "optional-team-uuid",
  "team_role": "team_member"
}
```

### Accept Invitation

```http
POST /api/b2b/invitations/join?token={invitation_token}
Authorization: Bearer {firebase_token}
```

### List Roles

```http
GET /api/b2b/roles
Authorization: Bearer {token}
```

### Get Team Roles

```http
GET /api/b2b/teams/team-roles
```

---

## Related Documentation

- [Tenant Admin Guide](./tenant-admin.md) - How to use the admin interface
- [Development Guide](./development.md) - Setting up the development environment
- [API Documentation](../api) - Complete API reference

---

## FAQ

**Q: Can a user have multiple tenant roles?**
No. Each user has exactly one tenant role.

**Q: Can a user be in multiple teams?**
Yes. A user can be a member of multiple teams with different team roles in each.

**Q: Who manages team membership?**
- Owners and Admins (organization-wide permission)
- Team Managers (for their specific team)

**Q: Can team roles override tenant roles?**
No. Tenant-level permissions take precedence. If your tenant role grants access, team role cannot restrict it.

**Q: How do I add custom roles?**
Custom tenant roles can be created via the Role Management interface. Team roles are fixed in the boilerplate.
