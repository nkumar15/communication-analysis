# User Management (B2B)

## 1. Context
### Goal
Manage the lifecycle of users within a Tenant Organization, including invitation, role assignment, status management, and removal.

### User Stories
- **As an Admin**, I want to list all users so that I can see who has access.
- **As an Admin**, I want to change a user's role so that I can promote them.
- **As an Owner**, I want to deactivate a user so that they can no longer access the system.

### Key Business Rules
**1. User Lifecycle**:
- **Invitation**: Email-based token flow.
- **Active**: Can login.
- **Inactive**: Blocked, but data preserved.

**2. Role Constraints**:
- `owner` cannot be removed if they are the last one.
- `member`/`viewer` roles cannot invite or update other users.

## 2. Architecture
### Security
- **RLS**: Strict tenant isolation on `users` table.
- **RBAC**: Endpoints protected by `users:write`, `users:invite`.

## 3. Database Schema
**Schema**: `b2b`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `users` | Tenant Members | `id`, `email`, `role_id`, `is_active` |
| `invitations` | Pending access | `id`, `email`, `role_id`, `token` |

## 4. API Reference
| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/b2b/users` | List tenant users | `users:read` |
| `POST` | `/api/b2b/invitations` | Invite user (Single) | `users:invite` |
| `PUT` | `/api/b2b/users/{id}/role` | Update role | `users:write` |
| `DELETE` | `/api/b2b/users/{id}` | Remove user | `users:delete` |
| `GET` | `/api/b2b/roles` | List available roles | `roles:read` |

## 5. Dependencies
- **Internal**: `services.invitation_service`, `services.rbac_service`
