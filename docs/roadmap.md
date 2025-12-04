# SaaS Boilerplate Roadmap

This document outlines the planned features and improvements for the Enterprise SSO SaaS Boilerplate.

## 🚀 Upcoming Features

### 1. Support Ticket System (Tier 1 Priority)
Internal help desk for tenants to request support.
- **Features:**
  - Ticket CRUD (Subject, Description, Priority, Category)
  - Commenting system (Internal vs Public notes)
  - Status tracking (Open, In Progress, Resolved, Closed)
  - Role-based access (Users see own, Admins see all)
- **Technical:**
  - Database tables: `support_tickets`, `support_ticket_comments`
  - API endpoints: `/api/b2b/support/*`

### 2. Billing & Invoicing (Tier 2 Priority)
Integration with payment providers (e.g., Stripe) for subscription management.
- **Features:**
  - Subscription plan selection
  - Payment method management
  - Invoice history and PDF download
  - Usage-based metering support

### 3. Advanced Security (Tier 2 Priority)
Enhanced security controls for enterprise tenants.
- **Features:**
  - Enforce 2FA/MFA for tenant users
  - Session management (view/revoke active sessions)
  - IP Allowlisting
  - Password policy configuration

### 4. Notifications Center (Tier 2 Priority)
Centralized notification system.
- **Features:**
  - In-app notifications
  - Email preferences
  - Webhook configuration for system events

### 5. Audit Logs Viewer (Tier 1 Priority)
UI for viewing system activity.
- **Features:**
  - Searchable/filterable table of user actions
  - Export to CSV/JSON
  - Retention policy settings

## 📦 Backlog / Nice-to-Have

- **API Keys Management:** UI for generating and revoking API keys.
- **Integrations Marketplace:** Directory of third-party integrations.
- **Reports & Analytics:** Visual dashboards for usage stats.
- **Localization:** Multi-language support for the admin portal.
