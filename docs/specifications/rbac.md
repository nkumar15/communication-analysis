# SPEC-03: Role-Based Access Control (RBAC)

**Status**: Active / Implemented
**Last Updated**: 2025-12-11

## Overview

The Authorization system controls user access to resources strictly based on their assigned **Role**. The system supports granular permissions defined as `resource:action` pairs.

## 1. Role Definitions

Roles are tenant-scoped but defined via global templates.

### 1.1 Tenant Roles (Global)
These roles apply to the entire workspace (Tenant).

| Role | Display Name | Description | Key Permissions |
|------|--------------|-------------|-----------------|
| `owner` | **Owner** | Primary administrator with total control. | **All Access** (Billing, Security, Deletion, Team Mgmt). |
| `admin` | **Admin** | Manager with full operational control. | **All Access** *except* Billing and Account Deletion. |
| `viewer` | **Viewer** | Read-only access to organization data. | **Read-only** for all functional modules. No Write/Delete. |

### 1.2 Team Roles (Contextual)
These roles apply within specific Teams (groups of users).

| Role | Display Name | Description | Key Permissions |
|------|--------------|-------------|-----------------|
| `team_manager` | **Team Manager** | Manages team membership and settings. | Invite/Remove members, Update team settings. |
| `team_member` | **Team Member** | Active participant in the team. | Read team info. (Domain specific: Edit tasks). |
| `team_viewer` | **Team Viewer** | Passive observer in the team. | Read-only access to team info and tasks. |

## 2. Resource & Permission Matrix

Permissions are granularly defined. Below is the mapping of Roles to Allowed Permissions.

### 2.1 Administration & System
| Resource | Action | Owner | Admin | Viewer |
|----------|--------|:-----:|:-----:|:------:|
| **Users** | `read` | ✅ | ✅ | ✅ |
| | `invite` | ✅ | ✅ | ❌ |
| | `delete` | ✅ | ❌ | ❌ |
| **Billing** | `manage` | ✅ | ❌ | ❌ |
| **Security** | `manage` | ✅ | ❌ | ❌ |
| **Audit Logs** | `read` | ✅ | ✅ | ❌ |

### 2.2 Domain Features (Task Management)
Domain-specific permissions are seeded dynamically.

| Resource | Action | Owner | Admin | Member* | Viewer |
|----------|--------|:-----:|:-----:|:-------:|:------:|
| **Projects** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ❌ | ❌ |
| | `delete` | ✅ | ✅ | ❌ | ❌ |
| **Tasks** | `read` | ✅ | ✅ | ✅ | ✅ |
| | `write` | ✅ | ✅ | ✅ | ❌ |
| **Comments** | `write` | ✅ | ✅ | ✅ | ❌ |

*(Member role usually aligns with Team Member scope)*

## 3. Scope & Data Access

Beyond permissions (`can do X`), access is also limited by **Scope** (`on which data`).

*   **Tenant Scope**: Owner/Admin can access **ALL** data within the tenant.
*   **Team Scope**:
    *   `team_manager` can manage their specific team's settings.
    *   `team_member` can see tasks assigned to their team.
*   **User Scope**: Users can always access their own profile and assigned items.

## 4. Implementation Details

*   **Enforcement**: Use `RequirePermission('resource', 'action')` decorator on API endpoints.
*   **Storage**:
    *   `b2b.roles`: Define roles.
    *   `b2b.role_permissions`: Map roles -> resource + action.
    *   `b2b.role_templates`: JSON templates for seeding new tenants.
