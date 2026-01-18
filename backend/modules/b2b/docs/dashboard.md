# Dashboard (B2B)

## 1. Context
### Goal
Provide role-appropriate views for all users, highlighting relevant information and actions based on responsibilities.

### User Stories
- **As an Owner**, I want an Billing & Health overview.
- **As an Admin**, I want to see pending User Invites.
- **As a Member**, I want to see **My Teams** and **My Tasks**.

### Key Business Rules
**1. Progressive Disclosure**:
- Members should NOT see Billing or Org Health.
- Only show widgets relevant to the user's role.

**2. Widget Permissions**:
- **Owner**: Full visibility (Org Health, Billing, Audit).
- **Admin**: Ops visibility (Users, Teams, Activity).
- **Member**: Team Scoped (My Teams, My Tasks).

## 2. Architecture
### Data Flow
- Frontend requests `/stats`.
- Backend determines `current_user.role`.
- Backend filters data and returns a `widgets` config.
- Frontend renders components dynamically based on config.

## 3. API Reference
| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/b2b/dashboard/stats` | Get Dynamic Stats | `dashboard:read` |

### Response Structure (Concept)
```json
{
  "role": "member",
  "widgets": {
    "my_teams": [...],
    "my_tasks": {"assigned": 5}
  }
}
```

## 4. Dependencies
- **Internal**: `services.dashboard_service`, `services.b2b.rbac`
