# Enterprise SSO - Multi-Tenant SaaS Boilerplate

Enterprise-grade multi-tenant SaaS application with **automated tenant provisioning**, SSO using OIDC, and Firebase Identity Platform.

## 🎯 Key Features

### Core Platform
- **Automated Tenant Onboarding** - CLI-driven tenant provisioning with zero manual configuration
- **Multi-Tenant Architecture** - Complete data isolation per tenant with team-based scoping  
- **Firebase GCIP** - Google Cloud Identity Platform for enterprise SSO
- **OIDC Integration** - Auth0, Okta, Azure AD, Google Workspace support
- **Stateless JWT Auth** - No session management, fully scalable

### User Management
- **Activation Workflow** - Self-service tenant activation via email link
- **Invitation System** - Role-based user invitations with email workflow
- **RBAC** - Granular permission system with resource-level access control
- **Teams** - Organize users into teams with isolated workspaces

### Domain Features  
- **Project Management** - Create and manage projects within teams
- **Task Tracking** - Assign tasks with status transitions and priority levels
- **Threaded Comments** - Contextual discussions on tasks with nested replies
- **Multi-Service Architecture** - Independent B2B, Platform, and B2C services


---

## 🧭 Documentation

### 🚀 Guides
*Practical "How-to" guides for developers and administrators.*

- **[Development Guide](docs/guides/development.md)**: Setup, local development, and coding standards.
- **[Deployment Guide](docs/guides/deployment.md)**: Deployment strategies and production configuration.
- **[Contributing](CONTRIBUTING.md)**: Guidelines for submitting PRs and reporting issues.
- **[Platform Admin Guide](docs/guides/platform-admin.md)**: Using the Super Admin Console and platform features.
- **[Tenant Admin Guide](docs/guides/tenant-admin.md)**: Instructions for tenant administrators.
- **[RBAC Concepts](docs/guides/rbac-concepts.md)**: Understanding the permission model.

### 📋 Specifications
*Detailed functional requirements and flow definitions.*

- **[Specifications Index](docs/specifications/README.md)**: Master list of all functional specifications.
- **[Tenant Onboarding](docs/specifications/tenant-onboarding.md)** (SPEC-01): Platform invite and activation flow.

### 🏗️ Architecture
*Technical design, concepts, and data flows.*

- **[Overview](docs/architecture/overview.md)**: High-level system architecture and tech stack.
- **[System Architecture](docs/architecture/system-architecture.md)**: Detailed component breakdown.
- **[Security](docs/architecture/security.md)**: Security best practices and implementation details.
- **[Onboarding Flow](docs/architecture/tenant-onboarding-flow.md)**: Detailed API sequence diagram for tenant creation and activation.
- **[Authentication](docs/architecture/authentication.md)**: Detailed API sequence diagram for authentication.    
- **[Authorization](docs/architecture/authorization.md)**: Technical deep dive into permission enforcement.
- **[Multi-Tenant Isolation](docs/architecture/multi-tenant-isolation.md)**: Detailed API sequence diagram for tenant isolation.
- **[UI Components](docs/architecture/ui-components.md)**: Design system and reusable frontend components.
- **[Domain APIs](docs/architecture/domain-apis.md)**: Projects, Tasks, and Comments APIs.
- **[B2C Module](docs/architecture/b2c-module.md)**: Personal and team workspace functionality.


### 🧪 Testing
*Quality assurance strategies and test plans.*

- **[Testing Strategy](docs/testing/strategy.md)**: Overall approach, tools, and roadmap.
- **[Testing Workflows](docs/testing/workflows.md)**: Manual and automated testing procedures.
- **[E2E Activation Tests](docs/testing/e2e-activation.md)**: Guide to testing the critical activation flow.

### 📅 Planning
*Project status, roadmap, and history.*

- **[Roadmap](docs/planning/roadmap.md)**: Future features and development plan.
- **[Completed Phases](docs/planning/completed-phases.md)**: History of delivered milestones.

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
