# B2C Module Folder Structure

## Scope
This structure applies to all code within the **B2C (Business-to-Consumer)** module.

## Backend Structure
Location: `backend/modules/b2c/`

| Folder | Purpose | Example Files |
|--------|---------|---------------|
| `models/` | SQLAlchemy ORM models | `user.py`, `workspace.py` |
| `routers/` | FastAPI API endpoint definitions | `users.py`, `workspaces.py` |
| `schemas/` | Pydantic request/response models | `users.py` |
| `services/` | Business logic layer | `user_service.py`, `subscription_service.py` |
| `middleware/` | Request lifecycle hooks | `auth.py` |

### File Naming Conventions
- **Models**: Singular noun (`user.py`, `workspace.py`)
- **Services**: Singular noun + `_service` suffix (`user_service.py`)
- **Routers**: Plural noun (`users.py`, `workspaces.py`)
- **Schemas**: Plural noun matching router (`users.py`)

## Frontend Structure
Location: `frontend/src/modules/b2c/`

| Folder | Purpose |
|--------|---------|
| `web/` | Web application code |
| `web/pages/` | Page-level React components |
| `web/components/` | Reusable UI components |
| `web/layouts/` | Page layout wrappers |
| `web/services/` | API client services |
| `mobile/` | Mobile application code (mirrors `web/` structure) |
| `pages/` | Root-level pages (legacy, prefer `web/pages/`) |
| `components/` | Root-level shared components (legacy) |
| `layouts/` | Root-level layouts (legacy) |

### Component Naming
- **Pages**: PascalCase with `Page` suffix (`DashboardPage.js`, `SettingsPage.js`)
- **Components**: PascalCase (`ProfileCard.js`, `SubscriptionBadge.js`)
- **Layouts**: PascalCase with `Layout` suffix (`MainLayout.js`)
