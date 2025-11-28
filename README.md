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
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

For detailed setup and testing instructions, see the [Development Guide](docs/guides/development.md).

---

## 🏗️ Architecture Overview

### Tech Stack
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, Firebase Admin SDK
- **Frontend:** React, Firebase SDK
- **Auth:** Firebase GCIP (OIDC), Stateless JWT

### Multi-Tenancy Model
- **Data Isolation:** Row-level security via `tenant_id`
- **Auth Isolation:** Separate Firebase tenants per customer
- **Platform Isolation:** Dedicated system tenant for super admins

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

