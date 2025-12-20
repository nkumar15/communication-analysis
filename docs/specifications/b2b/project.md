# Domain Logic Specification (Projects)

**ID**: `SPEC-05`
**Status**: Live
**Scope**: B2B Core Features

## 1. Overview
This specification defines the core domain entities: **Projects**, **Tasks**, and **Comments**. It outlines the hierarchy, team-based access control, and interaction logic.

## 2. Entity Hierarchy
1.  **Tenant**: The top-level container.
2.  **Team**: A group of users within a Tenant.
3.  **Project**: A workspace belonging to a specific Team.
4.  **Task**: A unit of work within a Project.
5.  **Comment**: A discussion entry on a Task.

## 3. Team-Based Scoping
- **Visibility**: Projects are **only** visible to members of the `Team` they belong to.
- **Creation**:
    - `Team Manager`: Can create projects.
    - `Team Contributor`: Can create projects (if granted `projects:write`).
    - `Team Reader`: Read-only.
- **Granular Permissions**:
    - Permissions are defined in `TeamRoleDefinition` JSON permissions (e.g., `projects:write`, `tasks:write`).

## 4. API Definition

### 4.1 Projects
| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/b2b/projects` | List projects (scoped to user's teams) | `projects:read`|
| `POST` | `/api/b2b/projects` | Create new project | `projects:write` |
| `GET` | `/api/b2b/projects/{id}` | Get details | `projects:read` |

### 4.2 Tasks
| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/b2b/projects/{id}/tasks` | Create task | `tasks:write` |
| `PATCH`| `/api/b2b/tasks/{id}` | Update status/assignee | `tasks:write` |

### 4.3 Comments
| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/b2b/tasks/{id}/comments` | Add comment | `comments:write` |

## 5. Business Logic & Constraints
- **Team Requirement**: Every project MUST belong to a valid Team.
- **Membership Check**: User must be an active member of the Project's Team to access it.
- **Status Workflow**: Task status transitions (TODO -> IN_PROGRESS -> DONE).

## 6. Testing Requirements
- **Isolation**: User in Team A cannot see Project in Team B.
- **RBAC**: `Team Reader` cannot create tasks.
- **Logic**: Creating a project with `team_id` the user doesn't belong to must fail (403/404).
