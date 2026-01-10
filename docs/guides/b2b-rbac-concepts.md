# Role-Based Access Control (RBAC) Guide

**Audience:** Developers and System Architects  
**Last Updated:** 2026-01-09

This guide explains the RBAC implementation in the SSO boilerplate, including configuration architecture, tenant roles, team roles, and customization workflows.

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Architecture](#configuration-architecture)
3. [Role Architecture](#role-architecture)
4. [Customization Workflows](#customization-workflows)
5. [Use Case Examples](#use-case-examples)
6. [Best Practices](#best-practices)

---

## Overview

The system implements a **two-level role system** with **flexible configuration**:

1. **Tenant Roles** - Organization-wide permissions (owner, admin, surveillance_chief, etc.)
2. **Team Roles** - Team-specific permissions (team_manager, desk_surveillance_manager, etc.)
3. **Configuration System** - YAML-based, supports core/domain/use_cases pattern

This pattern is used by GitHub, Slack, and Google Workspace for multi-tenant collaboration, extended with domain-specific customization.

---

## Configuration Architecture

### Directory Structure

```
backend/scripts/b2b/
├── core/                           # Universal SaaS (don't edit)
│   ├── actions.yaml
│   ├── saas_roles.yaml             # owner, admin, member, viewer
│   ├── saas_resources.yaml         # users, teams, billing, etc.
│   ├── team_roles_base.yaml        # team_manager, team_contributor, team_reader
│   └── README.md
│
├── domain/                         # YOUR customization
│   ├── resources.yaml
│   ├── tenant_roles.yaml
│   ├── team_roles.yaml
│   └── README.md
│
├── use_cases/                      # Demo templates
│   ├── bank_surveillance/
│   ├── marketing_agency/
│   └── task_management/
│
├── demo_configs/                   # Demo tenant seeds
│   ├── bank_surveillance_demo.json
│   ├── marketing_agency_demo.json
│   └── task_management_demo.json
│
├── subscription_plans.yaml
├── seed_rbac.py                    # Main seeding script
└── tenant_onboard.py
```

### Loading Logic

**Development/Demo (with USE_CASE):**
```bash
USE_CASE=bank_surveillance make b2b-seed-roles
# Loads: core/* + use_cases/bank_surveillance/*
```

**Production (without USE_CASE):**
```bash
make b2b-seed-roles
# Loads: core/* + domain/*
```

**Key Rule:** If use case/domain defines custom team roles, base team roles are **automatically skipped** (prevents role pollution).

---

## Role Architecture

### Three-Table Model

```
┌─────────────────────────────────────────────────────────┐
│ 1. role_templates (Global Blueprints)                  │
│    - Seeded from YAML                                   │
│    - Shared across all tenants                          │
│    - Contains permissions JSONB                         │
└─────────────────────────────────────────────────────────┘
                          ↓ (tenant creation)
┌─────────────────────────────────────────────────────────┐
│ 2. roles (Tenant-Specific Instances)                   │
│    - Created from templates                             │
│    - One set per tenant                                 │
│    - tenant_id + name unique                            │
└─────────────────────────────────────────────────────────┘
                          ↓ (user invitation)
┌─────────────────────────────────────────────────────────┐
│ 3. users (User Assignments)                            │
│    - users.role_id → roles.id                          │
│    - Each user has ONE tenant role                      │
└─────────────────────────────────────────────────────────┘
```

### Tenant Roles (Two Categories)

**A. Platform/SaaS Roles** (`core/saas_roles.yaml`)
- Universal across any business
- IT/operational focus
- Examples: `owner`, `admin`, `member`, `viewer`

**B. Domain-Specific Roles** (`domain/tenant_roles.yaml` or `use_cases/*/tenant_roles.yaml`)
- Business-specific roles
- Examples: `surveillance_chief`, `regional_director`, `agency_owner`

**Example Tenant Roles:**
```yaml
# core/saas_roles.yaml (Platform)
role_templates:
  - name: owner
    permissions:
      - resource: billing
        actions: [read, write, manage]
      - resource: users
        actions: [read, write, invite, delete]

# use_cases/bank_surveillance/tenant_roles.yaml (Domain)
tenant_roles:
  - name: surveillance_chief
    permissions:
      - resource: communications
        actions: [read, analyze, flag, export, archive]
      - resource: investigations
        actions: [read, create, assign, approve, close, export]
```

### Team Roles (Domain-Specific)

**Purpose:** Define capabilities within specific teams

**Conditional Loading:**
- If `domain/team_roles.yaml` is **empty** → Load base team roles
- If `domain/team_roles.yaml` has **custom roles** → **Skip** base team roles

**Example:**
```yaml
# use_cases/bank_surveillance/team_roles.yaml
team_roles:
  - name: desk_surveillance_manager
    display_name: Desk Surveillance Manager
    permissions:
      - resource: team_members
        actions: [manage]
      - resource: communications
        actions: [read, analyze, flag, export]
      - resource: investigations
        actions: [read, create, assign, approve, close]
```

---

## Customization Workflows

### Workflow 1: Starting from Scratch (Generic SaaS)

```bash
# Use task_management (generic base)
USE_CASE=task_management make b2b-seed-roles

# Result:
# - Tenant roles: owner, admin, member, viewer (from core/)
# - Team roles: team_manager, team_contributor, team_reader (from core/)
# - Resources: projects, tasks, comments (from use_cases/task_management/)
```

### Workflow 2: Copy from Demo Template

```bash
# Step 1: Choose template
cp -r use_cases/marketing_agency/* domain/

# Step 2: Customize for your client
nano domain/resources.yaml
nano domain/tenant_roles.yaml
nano domain/team_roles.yaml

# Step 3: Seed production
make b2b-seed-roles  # Loads domain/
```

### Workflow 3: Add Custom Role to Existing Setup

```yaml
# domain/tenant_roles.yaml
tenant_roles:
  - name: supervisor
    display_name: Supervisor
    description: Oversees operations without full admin access
    permissions:
      - resource: projects
        actions: [read, write]
      - resource: tasks
        actions: [read, write]
      - resource: users
        actions: [read]  # Can see but not modify users
      - resource: teams
        actions: [read, write]  # Can manage teams
```

Reseed:
```bash
make b2b-seed-roles
```

### Workflow 4: Add Custom Team Role

```yaml
# domain/team_roles.yaml
team_roles:
  - name: project_lead
    display_name: Project Lead
    permissions:
      - resource: team_members
        actions: [manage]  # Can add/remove team members
      - resource: team_settings
        actions: [manage]
      - resource: projects
        actions: [read, write, delete]
      - resource: tasks
        actions: [read, write, delete]
```

**Important:** Once you add ANY custom team role, base team roles are automatically skipped!

---

## Use Case Examples

### Bank Surveillance (Enterprise)

**Demo Tenant:** Worldwide Bank (`worldwidebank.com`)  
**Use Case:** `bank_surveillance`

This use case implements a **Hybrid RBAC Model** to satisfy banking regulations:
- Separation of Duties (Maker/Checker)
- Data Segregation (Chinese Walls between regional teams)
- Lead Privilege (Auditor access)

👉 **For the full guide on this use case, see:** [Bank Surveillance README](/home/neeraj/codes/enterprisesso/backend/scripts/b2b/use_cases/bank_surveillance/README.md)

### Marketing Agency (SME)

**Demo Tenant:** Merlion Marketing (`merlionmarketing.com`)  
**Use Case:** `marketing_agency`

**Tenant-Level Roles** (Organization-wide access):

| Role | Display Name | Example Email | Invitable? |
|------|--------------|---------------|------------|
| `owner` | Owner | `owner@merlionmarketing.com` | ❌ (Created at tenant setup) |
| `account_manager` | Account Manager | `john.smith@merlionmarketing.com` | ✅ |
| `creative_director` | Creative Director | `creative.director@merlionmarketing.com` | ✅ |
| `content_creator` | Content Creator | `designer@merlionmarketing.com` | ✅ |
| `marketing_specialist` | Marketing Specialist | `seo@merlionmarketing.com` | ✅ |

**Simple Role Hierarchy:**
```
owner (full access)
  ├── account_manager (client management, campaigns)
  ├── creative_director (design oversight, brand strategy)
  ├── content_creator (content production)
  └── marketing_specialist (SEO, analytics, social media)
```

**Role Examples:**
```yaml
# Agency Owner
email: owner@merlionmarketing.com
tenant_role: owner
can_access: everything (billing, users, all client data)
can_invite: all roles

# Account Manager
email: john.smith@merlionmarketing.com
tenant_role: account_manager
can_access: client accounts, campaigns, team collaboration
cannot_access: billing, platform settings
can_invite: yes (content creators, specialists)

# Creative Director
email: creative.director@merlionmarketing.com
tenant_role: creative_director
can_access: design assets, brand guidelines, creative review
cannot_access: billing, client contracts
can_invite: yes (designers, content creators)

# Content Creator
email: designer@merlionmarketing.com
tenant_role: content_creator
can_access: content production, asset library
cannot_access: billing, client management
can_invite: no

# Marketing Specialist (SEO)
email: seo@merlionmarketing.com
tenant_role: marketing_specialist
can_access: analytics, campaign performance, SEO tools
cannot_access: billing, design assets
can_invite: no
```

**Test Invitation Examples:**
```bash
# After running: make b2b-demo-marketing
# Login as: owner@merlionmarketing.com

# Invite team members:
john.smith@merlionmarketing.com → Account Manager
creative.director@merlionmarketing.com → Creative Director
designer@merlionmarketing.com → Content Creator
writer@merlionmarketing.com → Content Creator
seo@merlionmarketing.com → Marketing Specialist
social@merlionmarketing.com → Marketing Specialist
```

**Demo Commands:**
```bash
make b2b-demo-marketing  # Creates tenant + owner user
# UI: http://localhost:3001/b2b/users
```

---

## Best Practices

### 1. Start with a Use Case Template

**DON'T:**
```bash
# Start from scratch
nano domain/resources.yaml  # Empty file, no guidance
```

**DO:**
```bash
# Copy closest use case
cp -r use_cases/marketing_agency/* domain/
# Now customize from working baseline
```

### 2. Understand SoD Requirements

**Regulated Industries (Banks, Healthcare, Finance):**
- ✅ Separate `owner` (IT) from domain roles (business)
- ✅ Independent `compliance_officer` role
- ✅ Clear audit trail

**SMEs (Marketing, Consulting, Design):**
- ✅ Merge owner permissions into top business role (simpler)
- ✅ Fewer roles = easier to manage

### 3. Conditional Team Role Loading

**If using base team roles:**
```yaml
# domain/team_roles.yaml
team_roles: []  # Empty = use base team_manager, team_contributor, team_reader
```

**If defining custom team roles:**
```yaml
# domain/team_roles.yaml
team_roles:
  - name: project_lead
    # ... definition
  - name: developer
    # ... definition
# Base team roles automatically skipped!
```

### 4. Testing Checklist

- [ ] Owner can invite all roles
- [ ] Admin cannot access billing
- [ ] Member cannot invite users
- [ ] Viewer has read-only access
- [ ] Team manager can add team members
- [ ] Team roles work within team scope
- [ ] Switching USE_CASE loads correct resources
- [ ] Production (no USE_CASE) loads domain/ correctly

---

## Common Scenarios

### Scenario 1: Add Resource to Existing Deployment

```yaml
# domain/resources.yaml
resources:
  # ... existing resources
  
  - name: invoices  # NEW
    display_name: Invoices
    category: Finance
    description: Client invoicing and payments
```

**Grant permissions:**
```yaml
# domain/tenant_roles.yaml (add to relevant role)
  - name: agency_owner
    permissions:
      # ... existing permissions
      - resource: invoices  # NEW
        actions: [read, write, delete, export]
```

Reseed:
```bash
make b2b-seed-roles
```

### Scenario 2: Change Existing Role Permissions

```yaml
# domain/tenant_roles.yaml
# Change admin to have billing read access (not write):
  - name: admin
    permissions:
      - resource: billing
        actions: [read]  # Changed from no billing access
```

Reseed (idempotent):
```bash
make b2b-seed-roles
```

### Scenario 3: Client Needs Custom Approval Workflow

**This requires plugin architecture** (future enhancement). Current 2D RBAC doesn't support:
- Multi-step approval chains
- Conditional permissions based on resource state
- Time-based or location-based access

**See:** [RBAC Plugin Architecture](/home/neeraj/.gemini/antigravity/brain/08ab7912-d441-4df9-96a1-b63018c1569e/rbac_plugin_architecture.md)

---

## API Reference

### Seed RBAC

```bash
# Development/Demo:
USE_CASE=bank_surveillance make b2b-seed-roles

# Production:
make b2b-seed-roles
```

### Create Demo Tenant

```bash
make b2b-invite f=scripts/b2b/demo_configs/bank_surveillance_demo.json
```

### Check User Permissions (Backend)

```python
from modules.b2b.rbac.permission_checker import has_permission

# Tenant-level check
if await has_permission(user_id, 'projects', 'write', db):
    # User can write projects

# Team-level check
from modules.b2b.rbac.scope_checker import check_team_permission

if await check_team_permission(user_id, team_id, 'tasks', 'delete', db):
    # User can delete tasks in this team
```

---

## Related Documentation

- [RBAC Specification](../specifications/b2b/rbac.md) - Technical specification
- [Authorization Architecture](../architecture/b2b/authorization.md) - Deep technical dive
- [Enterprise Use Cases](/home/neeraj/.gemini/antigravity/brain/08ab7912-d441-4df9-96a1-b63018c1569e/enterprise_sme_use_cases.md) - Bank & Marketing examples

---

## FAQ



**Q: When are base team roles loaded?**
Only when use case/domain has NO custom team roles defined.

**Q: Can I have both platform and domain roles for the same user?**
Yes! User typically has: 1 platform role (e.g., `admin`) + can be assigned domain role (e.g., `regional_director`)

**Q: How do I switch between demo use cases?**
```bash
make b2b-demo-bank       # Switch to bank
make b2b-demo-marketing  # Switch to marketing
```

**Q: What if I need geographic boundaries or data classification?**
Current 2D RBAC doesn't support this. See [Plugin Architecture](/home/neeraj/.gemini/antigravity/brain/08ab7912-d441-4df9-96a1-b63018c1569e/rbac_plugin_architecture.md) for future enhancements.
