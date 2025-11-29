# Enterprise SSO - Multi-Tenant SaaS with Automated Onboarding

Enterprise-grade multi-tenant SaaS application with **automated tenant provisioning**, SSO using OIDC, and Firebase Identity Platform.

## 🎯 Key Features

- **Automated Tenant Onboarding** - CLI-driven tenant provisioning with zero manual configuration
- **Multi-Tenant Architecture** - Complete data isolation per tenant
- **Firebase GCIP** - Google Cloud Identity Platform for enterprise SSO
- **OIDC Integration** - Auth0, Okta, Azure AD, Google Workspace support
- **Activation Workflow** - Self-service tenant activation via email link
- **Invitation System** - Role-based user invitations with email workflow
- **Stateless JWT Auth** - No session management, fully scalable

---

## 🏗️ Architecture Overview

### Tech Stack

**Backend:**
- **FastAPI** - Modern async Python web framework
- **PostgreSQL** - Multi-tenant data storage with SQLAlchemy ORM
- **Firebase Admin SDK** - JWT validation & tenant management
- **Resend** - Transactional email service
- **Docker** - Containerized deployment

**Frontend:**
- **React 18** - Modern UI framework
- **Firebase SDK** - Client-side authentication
- **React Router** - SPA routing

### Multi-Tenancy Model

```
Company A (tenant_id=1)                     Company B (tenant_id=2)
├── Firebase Tenant: CompanyA-abc123       ├── Firebase Tenant: CompanyB-xyz789
├── OIDC Provider: Auth0                    ├── OIDC Provider: Okta
├── Domain: companya.com                    ├── Domain: companyb.com
├── Users:                                  ├── Users:
│   ├── admin@companya.com (admin)         │   ├── admin@companyb.com (admin)
│   └── user@companya.com (member)         │   └── user@companyb.com (member)
└── Data: Isolated in PostgreSQL            └── Data: Isolated in PostgreSQL
```

---

## 📚 Documentation

We have organized documentation by role:

| Role | Guide | Purpose |
|------|-------|---------|
| **Developer** | [Development Guide](docs/guides/development.md) | Setup, Testing, Architecture, CLI Tools |
| **Platform Admin** | [Platform Admin Guide](docs/guides/platform-admin.md) | SaaS Console, Tenant Management, System Config |
| **Tenant Admin** | [Tenant Admin Guide](docs/guides/tenant-admin.md) | User Management, Invitations, Dashboard Usage |

---

## 🚀 Quick Start

**Prerequisites:** Docker, Node.js 16+ (use `nvm`), Python 3.11+

```bash
# 1. Setup
git clone <repo>
cd enterprisesso
make setup

# 2. Configure
# Edit .env, backend/.env, frontend/.env
# Add secrets/firebase-credentials.json

# 3. Run
make up              # Start Backend
make frontend-start  # Start Frontend
```

**Access:**
- Frontend: http://localhost:3000
- **B2B API**: http://localhost:8000/docs (Tenant Management)
- **Platform API**: http://localhost:8001/docs (Admin Operations)
- **B2C API**: http://localhost:8002/docs (Workspaces)

For detailed setup and testing instructions, see the [Development Guide](docs/guides/development.md).

---

## 🏗️ Microservices Architecture

### Backend Services

The backend is split into 3 independent microservices:

| Service | Port | Purpose | Routers |
|---------|------|---------|---------|
| **B2B API** | 8000 | Enterprise tenant management | auth, activation, invitations, users, roles, farmers |
| **Platform API** | 8001 | SaaS platform administration | tenant mgmt, impersonation, stats |
| **B2C API** | 8002 | Personal/team workspaces | workspaces, profiles (skeleton) |

### Tech Stack
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, Firebase Admin SDK
- **Frontend:** React 18, Firebase SDK
- **Auth:** Firebase GCIP (OIDC), Stateless JWT
- **Deployment:** Docker, Docker Compose

### Key Architectural Patterns
- **Microservices**: Independent services for B2B, Platform, and B2C
- **Data Isolation**: Row-level security via `tenant_id` + PostgreSQL schemas
- **Auth Isolation**: Separate Firebase tenants per customer
- **Platform Isolation**: Dedicated `platform` schema for super admins
- **Shared Database**: All services use same PostgreSQL with schema separation

---

## 🔐 Security Features

- **JWT-based auth** - Stateless, scalable authentication
- **Firebase Admin SDK** - Cryptographically verified tokens
- **Multi-tenant isolation** - Data scoping by tenant_id
- **Role-based access** - Admin/manager/member permissions

See **[Security Policy](./SECURITY.md)** for detailed architecture.

---

## 📄 License

MIT

---

## 🆘 Support

- **Issues:** Check [Development Guide](docs/guides/development.md#troubleshooting)
- **API:** http://localhost:8000/docs

