# Navigation IA

## Primary Navigation

```
📊 Dashboard
👥 Team
├── Members
├── Roles
└── Groups
💳 Billing
├── Subscription
├── Invoices
└── Payment Methods
⚙️ Settings
├── General
├── Security
└── Audit Logs
👤 Profile
```

## Navigation Groups

| Group | Pages | Target Persona |
|-------|-------|----------------|
| **Admin** | Billing, Team, Settings (General, Security) | Tenant Owner |
| **User** | Dashboard, Profile | All Users |

## Permission-Based Visibility

| Navigation Item | Required Permission | Fallback |
|-----------------|---------------------|----------|
| Billing | `billing:read` | Hidden |
| Team | `users:read` | Hidden |
| Settings | `tenant:admin` | Hidden |
| Audit Logs | `audit:read` | Hidden |

## Page Hierarchy

```mermaid
graph TD
    A[Home/Dashboard] --> B[Billing]
    B --> B1[Subscription]
    B --> B2[Invoices]
    A --> C[Team]
    C --> C1[Members]
    C --> C2[Roles]
    A --> D[Settings]
    A --> E[Profile]
```

## Breadcrumb Patterns

| Page | Breadcrumb |
|------|------------|
| Dashboard | Home |
| Invoices | Home → Billing → Invoices |
| Members | Home → Team → Members |
