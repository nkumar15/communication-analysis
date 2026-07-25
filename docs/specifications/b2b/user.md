# User Management Specification

**ID**: `SPEC-04`
**Status**: Live
**Scope**: B2B Tenant Administration

## 1. Overview
This specification defines the lifecycle of users within a Tenant Organization, including invitation, role assignment, status management, and removal. It also covers the granular permission model for managing these users.

## 2. Terminology
- **Tenant User**: An account scoped to a specific Tenant Organization.
- **Role**: A named set of permissions (e.g., `owner`, `admin`, `member`, `viewer`) assigned to a user.
- **Invitation**: A time-limited token sent via email allowing an external person to join the Tenant.

## 3. User Lifecycle

### 3.1 Invitation
- **Mechanism**: Email-based invitation with a secure token.
- **Actors**: `owner`, `admin` (Tenant level).
- **Flow**:
    1.  Admin enters email + role.
    2.  System checks if user already exists in Tenant.
    3.  If new, creates `Invitation` record and sends email.
    4.  Recipient clicks link -> Authenticates -> Accepts -> User created/linked.

### 3.2 Role Management
- **Assignment**: Roles are assigned at creation (invitation) or updated via API.
- **Validation**: Role must exist in `roles` table.
- **Constraint**: `owner` role cannot be removed if it's the last one (manual check required, typically).

### 3.3 Status
- **Active**: Can login and access resources.
- **Inactive**: Blocked from access, but data preserved.
- **Deleted**: Soft-deleted (recoverable for audit) or Hard-deleted (GDPR).

## 4. API Definition

### 4.1 Endpoints

| Method | Endpoint | Description | Permission Required |
|--------|----------|-------------|---------------------|
| `GET` | `/api/b2b/users` | List all users in tenant | `users:read` |
| `POST` | `/api/b2b/invitations` | Invite a new user | `users:invite` |
| `PUT` | `/api/b2b/users/{id}/role` | Update user role | `users:write` |
| `DELETE` | `/api/b2b/users/{id}` | Remove user from tenant | `users:delete` |
| `GET` | `/api/b2b/roles` | List available tenant roles | `roles:read` |

### 4.2 Data Model
- **User**: `id`, `email`, `role_id`, `is_active`, `last_login`, `created_at`
- **Invitation**: `id`, `email`, `role_id`, `token`, `expires_at`, `invited_by`

## 5. Security Controls
- **RLS**: Users can only see/manage users within their own `tenant_id`.
- **RBAC**: `member` and `viewer` roles cannot invite or update roles.
- **Self-Modification**: Users typically cannot demote themselves or delete their own account (business rule).

## 6. Testing Requirements
- **Integration**: Verify invite -> accept flow.
- **Security**: Verify `member` cannot call `POST /invitations`.
- **Isolation**: Verify Tenant A cannot list Tenant B users.
