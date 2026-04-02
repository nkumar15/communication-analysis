# B2B Foundation Module

> The core multi-tenant SaaS framework providing authentication, billing, and team management.

## Overview

The B2B Foundation module provides the essential scaffolding for any multi-tenant application. It handles tenant isolation, user authentication, role-based access control (RBAC), subscription billing, and member management. This module ensures that data is strictly segregated between tenants while allowing for flexible team structures within a tenant.

## Target Platform
- [x] Web (React/Next.js)
- [ ] Mobile (iOS/Android)
- [x] Backend API Only

## Key Features

| Feature | Description | Status |
| :--- | :--- | :--- |
| **[Tenant Onboarding](./pages/onboarding.md)** | Self-service signup and activation flow. | ✅ Ready |
| **[SSO Integration](./features/authentication.md)** | OIDC/SAML support for Enterprise Identity. | ✅ Ready |
| **[User Invitations](./features/team_management.md)** | Role-based invites and bulk CSV options. | ✅ Ready |
| **[Audit Logs](./features/audit_logs.md)** | Immutable security trails for compliance. | ✅ Ready |
| **[Notifications](./features/notifications.md)** | Transactional emails and system alerts. | ✅ Ready |
| **[GenAI RAG](./features/genai_rag.md)** | AI-powered search and summarization (Domain). | 🔵 Available |

## Documentation

| Document | Description |
|----------|-------------|
| [Personas](./personas.md) | User personas and journeys |
| [Navigation](./navigation.md) | Information architecture |
| [Page Specs](./pages/) | Per-page specifications |
| [Technical](./technical/) | API, Schema, Architecture |

## Quick Links

### Product Docs
- [Personas](./personas.md) - Tenant Owner, Team Member
- [Navigation IA](./navigation.md)

### Page Specifications
- [Dashboard](./pages/dashboard.md)
- [Billing Settings](./pages/settings_billing.md)
- [Team Members](./pages/team_members.md)
- [Onboarding](./pages/onboarding.md)
- [Profile](./pages/profile.md)

### Technical Docs
- [API Reference](./technical/api.md)
- [Database Schema](./technical/schema.md)
- [Architecture](./technical/architecture.md)
