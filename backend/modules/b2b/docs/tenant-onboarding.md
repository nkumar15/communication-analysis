# Tenant Onboarding (B2B)

## 1. Context
### Goal
Automate the provisioning and activation of new Tenants via a vetted, invitation-based process (Not self-service).

### User Stories
- **As a Platform Admin**, I want to invite a company (Tenant) so that I can control who joins.
- **As a Tenant Owner**, I want to click a secure email link to activate my account.

### Key Business Rules
**1. Invitation Only**:
- Provisioning is triggered ONLY by Platform Admin.
- Tenants start in `PENDING` state.

**2. Activation Flow**:
- Link expire in 48 hours.
- Requires SSO Auth (OIDC) to verify identity during activation.
- Successful activation updates Tenant to `ACTIVE` and creates the `Owner` user.

**3. Multi-Platform Support**:
- Activation links must support Deep Linking (Open App if installed).

## 2. Architecture
### Flow State Machine
`PENDING` (Created) -> `ACTIVE` (Owner Logged In) -> `SUSPENDED` (Optional).

### Component Flow
1. Admin triggers Invite (`POST /api/platform/tenants`).
2. System creates Tenant + Token.
3. System sends Email.
4. User clicks Link -> Frontend calls `validate`.
5. User logs in -> Frontend calls `activate`.
6. System seeds initial data (Owner, Default Team).

## 3. Database Schema
**Schema**: `b2b`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `tenants` | Tenant Config | `id`, `name`, `status` (`PENDING`/`ACTIVE`), `activation_token` |
| `users` | Owner created here | `id`, `email`, `role` (`owner`) |

## 4. API Reference
| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| **Platform** | | | |
| `POST` | `/api/platform/tenants` | Create & Invite Tenant | `platform:admin` |
| **Public** | | | |
| `GET` | `/api/b2b/activate/validate/{token}` | Validate Token | Public |
| `POST` | `/api/b2b/activate` | Complete Activation | Public (Auth req) |

## 5. Dependencies
- **Internal**: `services.tenant_service`, `services.email_service`
- **External**: Deep Linking (Universal Links)
