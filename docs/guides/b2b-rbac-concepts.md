# Role-Based Access Control (RBAC) Guide

**Audience:** Developers and System Architects  
**Last Updated:** 2026-01-11

This guide explains the **3-Layer RBAC** implementation in the SSO boilerplate, based on enterprise design principles for regulated industries.

---

## Table of Contents

1. [Core Principle](#core-principle)
2. [The 3-Layer Model](#the-3-layer-model)
3. [System Roles](#system-roles)
4. [Tenant Roles](#tenant-roles)
5. [Team Memberships](#team-memberships)
6. [Permission Resolution](#permission-resolution)
7. [User Assignment Model](#user-assignment-model)
8. [UI/UX Best Practices](#uiux-best-practices)
9. [Golden Rules](#golden-rules)

---

## Core Principle

> **Separate WHY the user exists from WHAT the user can do**

Your confusion comes from mixing identity existence with business authority. The system has **3 distinct layers**, not 2:

| Layer | Purpose | Examples |
|-------|---------|----------|
| **System Role** | Platform-level baseline access | owner, admin, member, viewer |
| **Tenant Role** | Business function authority | surveillance_chief, analyst |
| **Team Membership** | Data scope | APAC, EMEA, India, SG |

Each layer answers a different question:

- **System role →** "Is this user allowed to use the system at all?"
- **Tenant role →** "What business function do they perform?"
- **Team →** "Which data are they allowed to see?"

---

## The 3-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: SYSTEM ROLE (Platform Access)                    │
│  • Required: Yes (exactly one)                             │
│  • Purpose: Login access, platform UI sections             │
│  • Examples: owner, admin, member, viewer                  │
│  • Controls: Can login, see admin console, manage billing  │
│  • Does NOT control: Business data access                  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: TENANT ROLE (Business Authority)                 │
│  • Required: No (0 to many)                                │
│  • Purpose: What business actions are allowed              │
│  • Examples: surveillance_chief, regional_director         │
│  • Controls: Allowed actions (analyze, approve, export)    │
│  • Does NOT control: Data scope                            │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: TEAM MEMBERSHIP (Data Scope)                     │
│  • Required: No (0 to many)                                │
│  • Purpose: Where permissions apply                        │
│  • Examples: APAC, SG Desk, Special Investigations         │
│  • Controls: Which data the user can see                   │
│  • Rule: Tenant role without team = no data scope          │
└─────────────────────────────────────────────────────────────┘
```

---

## System Roles

System roles are **immutable** and limited to a small, fixed set. Every user must have exactly one.

### Recommended System Roles

| Role | Purpose |
|------|---------|
| **owner** | Legal + billing + ultimate authority |
| **admin** | Tenant configuration & user management |
| **member** | Can log in and use assigned features |
| **viewer** | Read-only platform access |

### What System Roles Control

| Capability | owner | admin | member | viewer |
|------------|:-----:|:-----:|:------:|:------:|
| Login access | ✅ | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ | ✅ (read-only) |
| Manage users | ✅ | ✅ | ❌ | ❌ |
| Manage billing | ✅ | ❌ | ❌ | ❌ |
| Platform settings | ✅ | ✅ | ❌ | ❌ |
| Audit logs | ✅ | ✅ | ❌ | ❌ |

> ⚠️ **Rule:** System roles **never** grant access to business resources directly.

### What System Roles Do NOT Control

❌ Business data permissions (alerts, cases, investigations)  
❌ Resource-specific actions (analyze, approve, export)  
❌ Data scope (which team's data to see)

---

## Tenant Roles

Tenant roles define **what business actions are allowed**, independent of team scope.

### Purpose

These roles define:
- **Allowed actions** (analyze, approve, export)
- **Allowed resources** (alerts, cases, reports)

They do **NOT** define scope (which data).

### Examples

| Tenant Role | Display Name | Business Authority |
|-------------|--------------|-------------------|
| surveillance_chief | Chief Surveillance Officer | Global oversight of all surveillance |
| regional_director | Regional Director | Senior management for a region |
| head_compliance | Head of Compliance | Global regulatory oversight |

### Configuration

```yaml
# use_cases/bank_surveillance/tenant_roles.yaml
tenant_roles:
  - name: surveillance_chief
    display_name: Chief Surveillance Officer
    is_system_role: false  # Business role, not system role
    permissions:
      - resource: investigations
        actions: [read, create, assign, approve, close, export]
      - resource: alerts
        actions: [read, acknowledge, escalate, dismiss]
```

---

## Team Memberships

Teams answer **WHERE** permissions apply. They define the **data scope**.

### Purpose

| Concept | Example |
|---------|---------|
| Geographic | India, APAC, EMEA |
| Departmental | FX Desk, Bonds Desk |
| Functional | Special Investigations, Compliance |

### Key Rule

> **A tenant role without a team = no data scope**

A user with `surveillance_analyst` tenant role but no team assignment cannot see any business data.

### Team Roles

Within each team, users have a **team role** that defines their capabilities:

| Team Role | Capability |
|-----------|------------|
| surveillance_lead | Full management, approval authority |
| surveillance_analyst | Create/investigate cases |
| operations_maker | Create cases (no approval) |
| operations_checker | Approve cases (no creation) |
| guest_analyst | Read-only external access |

---

## Permission Resolution

Effective permissions are computed as:

```
System Access (can login?)
    + Tenant Role Permissions (what actions?)
        + Team Scope Filter (which data?)
```

### Permission Evaluation Logic

```python
def can_access(user, resource, action, data_team):
    # Layer 1: System Role Check
    if not user.system_role.allows_login:
        return False

    # Admin bypass for platform operations only
    if user.system_role.is_admin and resource.is_platform_resource:
        return True

    # Layer 2 + 3: Tenant Role + Team Scope
    for tenant_role in user.tenant_roles:
        if tenant_role.allows(resource, action):
            if data_team in user.teams:
                return True

    return False
```

### Permission Flow Diagram

```
User Request: "Can I approve this investigation in SG Desk?"
    │
    ▼
[LAYER 1] Does user have system role that allows login?
    │ YES
    ▼
[LAYER 2] Does user have tenant role with 'investigations:approve'?
    │ YES (surveillance_chief has this)
    ▼
[LAYER 3] Is user a member of 'SG Desk' team?
    │ YES
    ▼
✅ ACCESS GRANTED
```

---

## User Assignment Model

A user has:

```
User
 ├── System Role (required, exactly one)
 ├── Tenant Roles (0..n)
 └── Team Memberships (0..n)
```

### Default Assignment on User Creation

```
System Role = member
Tenant Roles = []
Teams = []
```

### What Default Users Can See

With only `member` system role (no tenant roles, no teams):

| Can See | Cannot See |
|---------|------------|
| ✅ Home / dashboard shell | ❌ Any business data |
| ✅ Profile page | ❌ Alerts / cases / reports |
| ✅ Notifications | ❌ Team-specific screens |
| ✅ "Request access" / "Awaiting assignment" | ❌ Any write actions |
| ✅ High-level tenant info (name, status) | |

> This prevents data leakage while avoiding user lockout.

### Common User Scenarios

| Scenario | System Role | Tenant Roles | Teams | Visibility |
|----------|-------------|--------------|-------|------------|
| New joiner | member | [] | [] | Dashboard shell only |
| External auditor | viewer | [compliance_officer] | [All] | Read-only reports |
| SG Desk Analyst | member | [] | [SG Desk: analyst] | SG data only |
| CSO | member | [surveillance_chief] | [Global] | All data |
| IT Admin | admin | [] | [] | User management, no business data |

---

## UI/UX Best Practices

### Situation-Based UI Behavior

| User State | UI Behavior |
|------------|-------------|
| No tenant roles | Show "No access assigned" message |
| Tenant role but no team | Show "Assign team to activate access" |
| Team but no role | Show "Role required" message |
| Viewer system role | Lock/hide write buttons |
| Admin system role | Show admin console |
| member with assignments | Show business data based on scope |

### Role Display

```json
{
  "user": {
    "system_role": "member",
    "tenant_roles": ["surveillance_chief"],
    "team_memberships": [
      {"team": "APAC Hub", "role": "oversight"},
      {"team": "SG Desk", "role": "surveillance_lead"}
    ]
  }
}
```

### Primary Display

- **Header/Profile:** Show system role badge (Member, Admin, Owner)
- **Secondary:** Show tenant role if assigned (Surveillance Chief)
- **Team Context:** Show current team scope in UI

---

## Golden Rules

1. **Every user must have exactly one system role**
2. **System role ≠ business access**
3. **Tenant roles define WHAT (actions)**
4. **Teams define WHERE (data scope)**
5. **No tenant role or no team = no business data**
6. **Default system role = member**
7. **Admins don't automatically get business data**
8. **Viewers have read-only platform access, not business data**

---

## Configuration Architecture

### Directory Structure

```
backend/scripts/b2b/
├── core/                           # Universal SaaS (don't edit)
│   ├── actions.yaml
│   ├── saas_roles.yaml             # System roles: owner, admin, member, viewer
│   ├── saas_resources.yaml         # Platform resources
│   └── team_roles_base.yaml        # Base team roles
│
├── domain/                         # YOUR customization
│   ├── resources.yaml              # Business resources
│   ├── tenant_roles.yaml           # Business tenant roles
│   └── team_roles.yaml             # Custom team roles
│
├── use_cases/                      # Demo templates
│   ├── bank_surveillance/
│   ├── marketing_agency/
│   └── task_management/
```

### Loading Logic

```bash
# Development/Demo (with USE_CASE):
USE_CASE=bank_surveillance make b2b-seed-roles
# Loads: core/* + use_cases/bank_surveillance/*

# Production (without USE_CASE):
make b2b-seed-roles
# Loads: core/* + domain/*
```

---

## Database Schema

### Three-Table Model

```sql
-- 1. Users with System Role
CREATE TABLE b2b.users (
    id UUID PRIMARY KEY,
    tenant_id UUID,
    role_id UUID REFERENCES b2b.roles(id),  -- System/Tenant role
    ...
);

-- 2. Team Memberships (Data Scope)
CREATE TABLE b2b.team_members (
    id UUID PRIMARY KEY,
    team_id UUID REFERENCES b2b.teams(id),
    user_id UUID REFERENCES b2b.users(id),
    team_role VARCHAR(50),  -- Role within this team
    ...
);

-- 3. Roles (System + Tenant)
CREATE TABLE b2b.roles (
    id UUID PRIMARY KEY,
    tenant_id UUID,
    name VARCHAR(50),
    is_system_role BOOLEAN,  -- true = system, false = tenant/business
    permissions JSONB,
    ...
);
```

---

## Related Documentation

- [Authorization Architecture](../architecture/b2b/authorization.md) - Technical implementation
- [Bank Surveillance Use Case](../../backend/scripts/b2b/use_cases/bank_surveillance/README.md) - Enterprise example
