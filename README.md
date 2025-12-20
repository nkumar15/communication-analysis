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

## 📦 Products

| Product | Description | Web | iOS | Android |
|---------|-------------|-----|-----|---------|
| **[B2B](docs/products/b2b/)** | Enterprise multi-tenant | ✅ | ✅ | ✅ |
| **[B2C](docs/products/b2c/)** | Personal workspaces | 🚧 | 🚧 | 🚧 |
| **[Platform](docs/products/platform/)** | SaaS admin console | ✅ | ❌ | ❌ |

---

## 🧭 Documentation

### 🚀 Guides
*Practical "How-to" guides for developers and administrators.*

- **[Development Guide](docs/guides/development.md)**: Setup, local development, and coding standards.
- **[Deployment Guide](docs/guides/deployment.md)**: Deployment strategies and production configuration.
- **[Mobile Development](docs/guides/mobile-development.md)**: React Native setup for B2B/B2C apps.
- **[Contributing](CONTRIBUTING.md)**: Guidelines for submitting PRs and reporting issues.
- **[Platform Admin Guide](docs/guides/platform-admin.md)**: Using the Super Admin Console and platform features.
- **[B2B Tenant Admin Guide](docs/guides/b2b-tenant-admin.md)**: Instructions for B2B tenant administrators.
- **[B2B RBAC Concepts](docs/guides/b2b-rbac-concepts.md)**: Understanding the B2B permission model.

### 📅 Planning
*Project status, roadmap, and history.*

- **[Roadmap](docs/planning/roadmap.md)**: Future features and development plan.
- **[Completed Phases](docs/planning/completed-phases.md)**: History of delivered milestones.

### 📋 Specifications
*Detailed functional requirements and flow definitions.*

- **[Specifications Index](docs/specifications/README.md)**: Master list of all functional specifications.
- **[Tenant Onboarding](docs/specifications/tenant-onboarding.md)** (SPEC-01): Platform invite and activation flow.

### 🏗️ Architecture
*Technical design, concepts, and data flows.*

#### Shared Architecture
- **[Overview](docs/architecture/overview.md)**: High-level system architecture and tech stack.
- **[System Architecture](docs/architecture/system-architecture.md)**: Detailed component breakdown.
- **[Security](docs/architecture/security.md)**: Security best practices and implementation details.
- **[UI Design](docs/architecture/ui-design.md)**: Design system and reusable frontend components.
- **[Domain APIs](docs/architecture/shared/domain-apis.md)**: Projects, Tasks, and Comments APIs.

#### B2B Architecture
- **[Authentication](docs/architecture/b2b/authentication.md)**: Authentication flow,tenant status validation, and RLS context.
- **[Authorization & RBAC](docs/architecture/b2b/authorization.md)**: Permission system, role templates, and tenant/user access control.
- **[Multi-Tenant Isolation](docs/architecture/b2b/multi-tenant-isolation.md)**: RLS implementation and tenant data isolation.
- **[Tenant Onboarding Flow](docs/architecture/b2b/tenant-onboarding-flow.md)**: Complete onboarding sequence from platform admin invite to activation.
- **[Subscription & Billing](docs/architecture/b2b/subscription.md)**: Pricing engine, payment flows, Stripe integration, and invoice management.


### 🧪 Testing
*Quality assurance strategies and test plans.*

- **[Testing Strategy](docs/testing/strategy.md)**: Overall approach, tools, and roadmap.
- **[Testing Workflows](docs/testing/workflows.md)**: Manual and automated testing procedures.
- **[B2B E2E Activation Tests](docs/testing/b2b-e2e-activation.md)**: Guide to testing the critical activation flow.

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
make up          # Start Backend Services
make web-b2b     # Start B2B Frontend (port 3000)
# OR
make dev-b2b     # Start both backend + B2B frontend
```

**Multi-Portal Commands:**
```bash
make web-b2b       # B2B portal (port 3000)
make web-b2c       # B2C portal (port 3001)
make web-platform  # Platform portal (port 3002)
```

**Access:**
- **B2B Portal**: http://localhost:3000
- **B2C Portal**: http://localhost:3001
- **Platform Portal**: http://localhost:3002
- **API Gateway**: http://localhost:8080

For detailed setup and testing instructions, see the [Development Guide](docs/guides/development.md).

---

## 📄 License

MIT
