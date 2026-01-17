# B2B Module Folder Structure

## Scope
This structure applies to all code within the **B2B (Business-to-Business)** module.

## Backend Structure
Location: `backend/modules/b2b/`

| Folder | Purpose | Example Files |
|--------|---------|---------------|
| `models/` | SQLAlchemy ORM models | `user.py`, `team.py`, `invitation.py` |
| `routers/` | FastAPI API endpoint definitions | `users.py`, `teams.py`, `auth.py` |
| `schemas/` | Pydantic request/response models | `users.py`, `teams.py` |
| `services/` | Business logic layer | `user_service.py`, `team_service.py` |
| `middleware/` | Request lifecycle hooks | `auth.py`, `tenant.py` |
| `rbac/` | Permission checking logic | `__init__.py`, `has_permission.py` |
| `utils/` | Shared utilities | `csv_parser.py` |
| `tasks/` | Celery background tasks | `email_tasks.py` |

### File Naming Conventions
- **Models**: Singular noun (`user.py`, `team.py`)
- **Services**: Singular noun + `_service` suffix (`user_service.py`)
- **Routers**: Plural noun (`users.py`, `teams.py`)
- **Schemas**: Plural noun matching router (`users.py`)

## Frontend Structure
Location: `frontend/src/modules/b2b/`

| Folder | Purpose |
|--------|---------|
| `web/` | Web application code |
| `web/pages/` | Page-level React components |
| `web/components/` | Reusable UI components |
| `web/layouts/` | Page layout wrappers |
| `mobile/` | Mobile application code (mirrors `web/` structure) |
| `billing/` | Stripe/billing components |
| `constants/` | Shared constants and enums |

### Component Naming
- **Pages**: PascalCase with `Page` suffix (`TeamsPage.js`, `DashboardPage.js`)
- **Components**: PascalCase (`TeamCard.js`, `UserTable.js`)
- **Layouts**: PascalCase with `Layout` suffix (`DashboardLayout.js`)
