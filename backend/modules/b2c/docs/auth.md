# Authentication (B2C)

## 1. Context
### Goal
Provide secure authentication for individual users, ensuring every user has a Personal Workspace upon entry.

### User Stories
- **As a User**, I want to sign up with Google so I don't have to remember passwords.
- **As a User**, I want my account to be ready (with a workspace) immediately after signup.

### Key Business Rules
**1. Auto-Provisioning**:
- Every B2C user MUST have a Personal Workspace (`default_workspace_id`).
- Signup/Login endpoints automatically create this if missing.

**2. Identity**:
- Managed by Firebase Auth.
- Backend verifies `id_token` and syncs to `b2c.users`.

**3. Idempotency**:
- `POST /login` handles "Get or Create" logic, ensuring smooth onboarding if the explicit Signup step was skipped (e.g. Social Login).

## 2. Architecture
### Data Flow
```mermaid
graph TD
    Client[Frontend] -->|1. Auth with Google| Firebase[Firebase Auth]
    Firebase -->|2. ID Token| Client
    Client -->|3. Send Token| API[Backend API]
    API -->|4. Verify Token| Admin[Firebase Admin SDK]
    API -->|5. Sync/Create| DB[(Database)]
    DB -->|6. Return User + Workspace| API
```

### Database Schema
**Schema**: `b2c`
- `users`: `id`, `email`, `firebase_uid`, `default_workspace_id`.

## 3. API Reference
**Base Path**: `/api/b2c/auth`

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/signup` | Create Account + Workspace | ID Token |
| `POST` | `/login` | Login (Get or Create) | ID Token |
| `GET` | `/me` | Get Profile + Workspaces | Session |

## 4. Dependencies
- **Internal**: `services.auth_service`
- **External**: Firebase Auth
