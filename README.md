# Enterprise SSO - Multi-Tenant SaaS Boilerplate

Enterprise-grade multi-tenant SaaS application with **automated tenant provisioning**, SSO using OIDC, and Firebase Identity Platform.

## 🎯 Key Features

- **Automated Tenant Onboarding** - CLI-driven tenant provisioning with zero manual configuration
- **Multi-Tenant Architecture** - Complete data isolation per tenant
- **Firebase GCIP** - Google Cloud Identity Platform for enterprise SSO
- **OIDC Integration** - Auth0, Okta, Azure AD, Google Workspace support
- **Activation Workflow** - Self-service tenant activation via email link
- **Invitation System** - Role-based user invitations with email workflow
- **Stateless JWT Auth** - No session management, fully scalable
- **Microservices** - Independent B2B, Platform, and B2C services

---

## 🧭 Documentation

We have organized documentation by role in the `docs/` directory.

| Role | Guide | Purpose |
|------|-------|---------|
| **Developer** | [Development Guide](docs/guides/development.md) | Setup, Testing, Architecture, CLI Tools |
| **Platform Admin** | [Platform Admin Guide](docs/guides/platform-admin.md) | SaaS Console, Tenant Management, System Config |
| **Tenant Admin** | [Tenant Admin Guide](docs/guides/tenant-admin.md) | User Management, Invitations, Dashboard Usage |

### 📚 [Full Documentation Index](docs/README.md)

- **[System Architecture](docs/architecture/overview.md)**
- **[API Documentation](http://localhost:8000/docs)**
- **[Roadmap](docs/planning/roadmap.md)**

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
make up              # Start Backend Services
make frontend-start  # Start Frontend
```

**Access:**
- **Frontend**: http://localhost:3000
- **B2B API**: http://localhost:8000/docs
- **Platform API**: http://localhost:8001/docs
- **B2C API**: http://localhost:8002/docs

For detailed setup and testing instructions, see the [Development Guide](docs/guides/development.md).

---

## 📄 License

MIT
