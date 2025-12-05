# Domain APIs Architecture

This document describes the core domain APIs for Projects, Tasks, and Comments functionality.

## Overview

The domain APIs provide a complete project management and collaboration system with:
- **Projects** - Organize work within teams
- **Tasks** - Track and assign work items  
- **Comments** - Contextual discussions with threaded replies

All domain resources enforce multi-tenant isolation and team-based scoping.

## Multi-Tenant Architecture

### Isolation Levels

1. **Tenant Level** - All resources belong to exactly one tenant
2. **Team Level** - Projects are scoped to teams within a tenant
3. **User Level** - Access controlled by team membership and RBAC permissions

### Data Model

```
Tenant
  └── Team(s)
       └── Project(s)
            └── Task(s)
                 └── Comment(s)
```

## Projects API

**Endpoint:** `/api/b2b/projects`

### Features

- Create projects within teams
- List projects (scoped by team membership for members, all for owners/admins)
- Update project details
- Archive/unarchive projects
- Delete projects (hard delete)

### Access Control

- **Create:** Must be team member
- **Read:** Team members see their team's projects, owners/admins see all
- **Update/Delete:** Requires write permission + team membership

### Key Endpoints

```
POST   /api/b2b/projects          # Create project
GET    /api/b2b/projects          # List projects (team-scoped)
GET    /api/b2b/projects/{id}     # Get project details
PUT    /api/b2b/projects/{id}     # Update project
DELETE /api/b2b/projects/{id}     # Delete project
```

## Tasks API

**Endpoint:** `/api/b2b/tasks`

### Features

- Create tasks within projects
- Assign tasks to team members
- Update task status (todo → in_progress → done)
- Filter tasks by project, status, assignee
- Track task priority and due dates

### Task Status Flow

```
todo → in_progress → done
```

Status transitions enforced via `PATCH /api/b2b/tasks/{id}/status`

### Access Control

- **Create:** Must have access to parent project
- **Read:** Same as project access
- **Update:** Requires write permission
- **Assign:** Can only assign to team members

### Key Endpoints

```
POST   /api/b2b/tasks                    # Create task
GET    /api/b2b/tasks                    # List tasks (filterable)
GET    /api/b2b/tasks/{id}               # Get task details
PUT    /api/b2b/tasks/{id}               # Update task
PATCH  /api/b2b/tasks/{id}/status        # Update status
DELETE /api/b2b/tasks/{id}               # Delete task
```

### Query Parameters

- `project_id` - Filter by project
- `status` - Filter by status (`todo`, `in_progress`, `done`)
- `assigned_to` - Filter by assignee

## Comments API

**Endpoint:** `/api/b2b/comments`

### Features

- Add comments to tasks
- Threaded replies (parent-child relationships)
- Update own comments
- Delete own comments (owners can delete any)
- List comments in threaded structure

### Threading Model

```python
Comment {
  id: UUID
  task_id: UUID
  parent_comment_id: UUID | null  # null = top-level
  content: str
  created_by: UUID
  replies: List[Comment]  # Populated for list endpoint
}
```

### Access Control

- **Create:** Must have access to parent task
- **Read:** Same as task access
- **Update:** Own comments only (unless owner/admin)
- **Delete:** Own comments only (unless owner/admin)

### Key Endpoints

```
POST   /api/b2b/comments              # Create comment
GET    /api/b2b/comments/task/{id}    # List comments (threaded)
PUT    /api/b2b/comments/{id}         # Update comment
DELETE /api/b2b/comments/{id}         # Delete comment
```

### Response Schemas

- **Single comment** (create/update): `CommentResponse` (no `replies` field)
- **List comments**: `CommentResponseWithReplies[]` (includes nested `replies`)

This prevents lazy-loading issues while supporting threaded display.

## RBAC Integration

### Required Permissions

All endpoints use the `@require_permission` decorator:

```python
@require_permission('projects', 'read')   # or 'write', 'delete'
@require_permission('tasks', 'read')
@require_permission('comments', 'read')
```

### Permission Bypass

Currently, `owner`, `admin`, and `team_member` roles bypass permission checks (TODO: implement `is_superuser` flag).

### Team-Based Scoping

Even with permissions, users can only access resources from:
1. Their own tenant (tenant isolation)
2. Teams they are members of (team scoping)

The `scope_checker.py` module enforces these rules:
- `can_user_access_team()` - Verifies team membership
- `can_access_project()` - Checks project.team ownership
- `can_access_task()` - Checks task.project.team ownership

## Multi-Tenant Isolation

### Tenant ID Enforcement

All access control functions accept `user_tenant_id` parameter:

```python
async def can_access_project(
    user_id: UUID,
    project_id: UUID,
    user_role: str,
    user_tenant_id: UUID,  # ← Enforces isolation
    db: AsyncSession
) -> bool:
    # Verify project.team.tenant_id == user_tenant_id
```

### Status Codes

- **403 Forbidden** - User lacks permission or crosses tenant boundary
- **404 Not Found** - Resource genuinely doesn't exist (after permission check)

Priority: Security (403) over information disclosure (404)

## Testing

### Test Coverage

All domain APIs have comprehensive integration tests:
- `tests/e2e_api/domain/test_projects.py` (10 tests)
- `tests/e2e_api/domain/test_tasks.py` (11 tests)
- `tests/e2e_api/domain/test_comments.py` (10 tests)

### Test Scenarios

- ✅ CRUD operations
- ✅ Multi-tenant isolation
- ✅ Team-based scoping
- ✅ Role-based permissions
- ✅ Assignment validation (tasks)
- ✅ Threading structure (comments)

### Running Tests

```bash
# Domain API tests only
docker-compose run --rm e2e-tests pytest tests/e2e_api/domain/ -v

# All backend tests
docker-compose run --rm e2e-tests pytest -v
```

## Database Schema

### Key Tables

**`projects.projects`**
```sql
id              UUID PRIMARY KEY
tenant_id       UUID NOT NULL REFERENCES b2b.tenants
team_id         UUID NOT NULL REFERENCES b2b.teams
name            VARCHAR(255) NOT NULL
description     TEXT
status          VARCHAR(50) DEFAULT 'active'
created_by      UUID REFERENCES b2b.users
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**`projects.tasks`**
```sql
id              UUID PRIMARY KEY
project_id      UUID NOT NULL REFERENCES projects.projects
title           VARCHAR(255) NOT NULL
description     TEXT
status          task_status_enum DEFAULT 'todo'
priority        priority_enum
assigned_to     UUID REFERENCES b2b.users
due_date        TIMESTAMP
created_by      UUID REFERENCES b2b.users
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**`projects.comments`**
```sql
id                  UUID PRIMARY KEY
tenant_id           UUID NOT NULL REFERENCES b2b.tenants
task_id             UUID NOT NULL REFERENCES projects.tasks
parent_comment_id   UUID REFERENCES projects.comments
content             TEXT NOT NULL
created_by          UUID NOT NULL REFERENCES b2b.users
created_at          TIMESTAMP
updated_at          TIMESTAMP
deleted_at          TIMESTAMP  # Soft delete
```

## Future Enhancements

- [ ] Webhooks for task status changes
- [ ] File attachments on tasks/comments
- [ ] Project templates
- [ ] Task dependencies and subtasks
- [ ] Activity timeline/audit log
- [ ] Real-time updates via WebSockets
- [ ] Bulk operations (mark multiple tasks complete)
- [ ] Custom fields per tenant
