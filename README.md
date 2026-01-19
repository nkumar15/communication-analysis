# Enterprise SaaS Accelerator

> **The Operating System for Multi-Tenant B2B & B2C Applications.**
> Built with FastAPI, React, and Firebase Identity Platform.

## 🚀 Overview

This accelerator provides a production-ready foundation for building scalable, multi-tenant SaaS products. Instead of reinventing authentication, billing, and isolation for every new project, developers can start building **Domain Value** immediately.

**Key Capabilities:**
- **🏢 Multi-Tenancy**: Strict data isolation using Row-Level Security (RLS).
- **🔐 Enterprise Identity**: OIDC (Okta/Google), SAML, and MFA via Firebase GCIP.
- **💳 Unified Billing**: Subscription management, invoices, and payment/seat provisioning.
- **👥 Team Management**: Granular RBAC, Invites, and Team hierarchies.

---

## 📦 Product Portfolio

The repository is organized into **Foundational Modules** (The Platform) and **Commercial Verticals** (The Products).

### 🏗️ Foundation Modules
*Core infrastructure shared across all products.*

| Module | Description | Key Features | Docs |
| :--- | :--- | :--- | :--- |
| **[B2B Core](backend/modules/b2b/README.md)** | The Business SaaS Engine | Tenant Isolation, Billing, RBAC | [Docs](backend/modules/b2b/docs/README.md) |
| **[Platform](backend/modules/platform/README.md)** | Super-Admin Console | Tenant Provisioning, Analytics | [Docs](backend/modules/platform/README.md) |
| **[B2C Core](backend/modules/b2c/README.md)** | Consumer Apps | User Profiles, Personal Workspaces | [Docs](backend/modules/b2c/README.md) |

### 🚀 Commercial Verticals
*Real-world domain applications built on top of the Foundation.*

| Product | Domain | Description | Status |
| :--- | :--- | :--- | :--- |
| **[Bank Surveillance](backend/modules/domains/b2b/bank_surveillance/README.md)** | FinTech / Compliance | **AI-Powered Communication Surveillance**. Detects insider trading, collusion, and fraud using RAG and Graph Analysis on the Enron dataset. | 🟡 Beta |
| **Finance Trader** | FinTech / Retail | Personal finance and trading dashboard. | 🚧 WiP |

---

## 🧭 Developer Experience

### Quick Start

**Prerequisites:** Docker, Node.js 16+, Python 3.11+

```bash
# 1. Setup
git clone <repo>
cd enterprisesso
make setup

# 2. Start Services
make dev-b2b     # Starts Backend + B2B Frontend (localhost:3000)
```

### Access Points
- **B2B Portal**: http://localhost:3000
- **Platform Console**: http://localhost:3002
- **API Gateway**: http://localhost:8080

### Documentation Index
- **[Development Guide](docs/guides/development.md)**: Setup, Standards, workflows.
- **[Architecture Overview](docs/architecture/overview.md)**: System design and patterns.
- **[Testing Standards](docs/standards/testing.md)**: Strategy and coverage.

---

## 📄 License
MIT
