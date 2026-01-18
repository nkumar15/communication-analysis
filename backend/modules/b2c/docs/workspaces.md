# Workspaces (B2C)

## 1. Context
### Goal
Provide isolated environments for users to manage their resources, supporting both Personal (Single-User) and Team (Multi-User) collaboration.

### User Stories
- **As a User**, I want a Personal Workspace auto-created on signup so I can start immediately.
- **As a Power User**, I want to create a Team Workspace so I can collaborate with others.
- **As a Team Owner**, I want to invite members and assign roles (Admin/Viewer) to control access.

### Key Business Rules
**1. Workspace Types**:
- **Personal**: Auto-created, Single User, Free.
- **Team**: Created by user, Multi-user, Requires Premium Subscription.

**2. Membership Roles**:
- **Owner**: Full control, Billing responsibilities. Cannot be removed.
- **Admin**: Manage members and settings.
- **Member**: Create/Edit resources.
- **Viewer**: Read-only.

**3. Isolation**:
- Resources are scoped to `workspace_id`.
- Users can only access workspaces they are members of (RLS).

## 2. Architecture
### Database Schema
**Schema**: `b2c`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `workspaces` | Workspace Entity | `id`, `owner_id`, `type` (personal/team) |
| `workspace_members` | Membership | `workspace_id`, `user_id`, `role` |

### Data Flow
```mermaid
graph TD
    User[User] -->|API Request| Router[WorkspaceRouter]
    Router -->|Check Membership| Middleware[Auth Middleware]
    Middleware -->|Deny| 403[Forbidden]
    Middleware -->|Allow| Service[WorkspaceService]
    Service -->|Query Scoped by ID| DB[(Database)]
```

### RLS Strategy
Queries are scoped by `workspace_id`.
Middleware ensures user is a valid member before allowing access.

## 3. API Reference
**Base Path**: `/api/b2c/workspaces`

| Method | Endpoint | Description | Role Req |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | List my workspaces | Any |
| `POST` | `/` | Create Team Workspace | Premium |
| `GET` | `/{id}` | Get Details + Members | Member |
| `PATCH` | `/{id}` | Update Settings | Admin |
| `DELETE` | `/{id}` | Delete Workspace | Owner |
| **Members** | | | |
| `GET` | `/{id}/members` | List Members | Member |
| `PATCH` | `/{id}/members/{uid}` | Update Role | Admin |
| `DELETE` | `/{id}/members/{uid}` | Remove Member | Admin |

## 4. Dependencies
- **Internal**: `services.workspace_service`, `services.auth_service`
