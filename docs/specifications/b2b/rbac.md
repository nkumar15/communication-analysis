# SPEC-03: Role-Based Access Control (RBAC)

**Status**: Active / Implemented  
**Last Updated**: 2026-01-09

---

## Overview

The authorization system uses a **two-dimensional access control** model:

| Dimension | Question | Controlled By |
|-----------|----------|---------------|
| **Permission** | "Can I do this action?" | Tenant Role |
| **Scope** | "On which data?" | Team Membership |

---

## 1. Configuration Architecture

### 1.1 Directory Structure

```
backend/scripts/b2b/
├── core/                           # Universal SaaS boilerplate (DON'T EDIT)
│   ├── actions.yaml                # Universal actions (read, write, delete, etc.)
│   ├── saas_roles.yaml             # Platform roles (owner, admin, member, viewer)
│   ├── saas_resources.yaml         # Platform resources (users, teams, billing, etc.)
│   ├── team_roles_base.yaml        # Generic team roles (team_manager, etc.)
│   └── README.md
│
├── domain/                         # Your production customization (EDIT THIS)
│   ├── resources.yaml              # Client-specific resources
│   ├── tenant_roles.yaml           # Additional tenant-level roles
│   ├── team_roles.yaml             # Additional team-level roles
│   ├── tenant_permissions.yaml     # Custom permission mappings
│   ├── team_permissions.yaml       # Custom team permission mappings
│   └── README.md
│
├── use_cases/                      # Demo templates (COPY TO domain/)
│   ├── bank_surveillance/          # Enterprise banking demo
│   ├── marketing_agency/           # SME agency demo
│   └── task_management/            # Generic SaaS demo
│
├── demo_configs/                   # Demo tenant seed files
│   ├── bank_surveillance_demo.json
│   ├── marketing_agency_demo.json
│   └── task_management_demo.json
│
├── subscription_plans.yaml         # Billing tiers
├── seed_rbac.py                    # Main seeding script
└── tenant_onboard.py               # Tenant creation CLI
```

### 1.2 Configuration Loading Logic

The `seed_rbac.py` script loads configurations based on the `USE_CASE` environment variable:

```bash
# Load specific use case (demo/testing):
USE_CASE=bank_surveillance python seed_rbac.py
# Loads: core/* + use_cases/bank_surveillance/*

# Load production customization (no USE_CASE):
python seed_rbac.py
# Loads: core/* + domain/*
```

**Loading order:**
1. **Always:** `core/` (actions, saas_roles, saas_resources, team_roles_base*)
2. **Conditionally:**
   - If `USE_CASE` set → `use_cases/<USE_CASE>/`
   - If no `USE_CASE` → `domain/`

**Important:** Base team roles (`team_roles_base.yaml`) are **skipped** if the use case/domain defines custom team roles, preventing role pollution.

---

## 2. Database Schema

### 2.1 Three-Table Model

```sql
-- Table 1: Global Role Templates (blueprints)
CREATE TABLE b2b.role_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 'owner', 'surveillance_chief', etc.
    display_name VARCHAR(100),
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    permissions JSONB NOT NULL,                 -- [{"resource":"users","actions":["read","write"]}]
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Table 2: Tenant-Specific Role Instances
CREATE TABLE b2b.roles (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    name VARCHAR(50) NOT NULL,                  -- Same as template name
    display_name VARCHAR(100),
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    UNIQUE(tenant_id, name)
);

-- Table 3: User Role Assignments
CREATE TABLE b2b.users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    email VARCHAR(255) NOT NULL,
    role_id UUID REFERENCES b2b.roles(id),      -- User's assigned role
    -- ... other fields
);
```

### 2.2 Team Role Definitions

```sql
CREATE TABLE b2b.team_role_definitions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),   -- NULL = global/system role
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    permissions JSONB NOT NULL,                  -- [{"resource":"tasks","actions":["read","write"]}]
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE b2b.team_members (
    id UUID PRIMARY KEY,
    team_id UUID REFERENCES b2b.teams(id),
    user_id UUID REFERENCES b2b.users(id),
    team_role_id UUID REFERENCES b2b.team_role_definitions(id),
    -- ... other fields
);
```

### 2.3 Data Flow

```
SEEDING (seed_rbac.py):
    YAML files → role_templates table (global definitions)

TENANT ONBOARDING:
    role_templates → roles table (tenant-specific instances)

USER INVITATION:
    roles table → users.role_id (user assignment)
```

---

## 3. Tenant Roles vs Team Roles

### 3.1 Tenant-Level Roles (Cross-Team Permissions)

**Purpose:** Define what actions a user can perform across the entire tenant

**Two Categories:**

**A. Platform/SaaS Roles** (`core/saas_roles.yaml`)
- Universal IT/operational roles
- Every SaaS needs these
- Examples: `owner`, `admin`, `member`, `viewer`

**B. Domain-Specific Roles** (`domain/tenant_roles.yaml` or `use_cases/*/tenant_roles.yaml`)
- Business-specific roles
- Examples: `surveillance_chief`, `regional_director`, `agency_owner`

| Role | Category | Scope | Key Permissions |
|------|----------|-------|-----------------|
| `owner` | Platform | All teams | Billing, user management, platform settings |
| `admin` | Platform | Assigned teams | User management (no billing) |
| `member` | Platform | Assigned teams | Standard access |
| `viewer` | Platform | Assigned teams | Read-only |
| `surveillance_chief` | Domain (Bank) | All teams | Surveillance operations + platform admin |
| `agency_owner` | Domain (Marketing) | All teams | Agency management + platform admin |

### 3.2 Team-Level Roles (Team-Specific Permissions)

**Purpose:** Define a user's capabilities within a specific team

**Two Categories:**

**A. Generic Team Roles** (`core/team_roles_base.yaml`)
- Universal team management
- Examples: `team_manager`, `team_contributor`, `team_reader`
- **Only loaded if use case has NO custom team roles**

**B. Domain-Specific Team Roles** (`domain/team_roles.yaml` or `use_cases/*/team_roles.yaml`)
- Business-specific team roles
- Examples: `desk_surveillance_manager`, `account_manager`, `creative_lead`
- **If defined, base team roles are SKIPPED** (prevents pollution)

---

## 4. Separation of Duties (SoD) Patterns

### 4.1 Pattern A: Regulated Industries (Banks, Healthcare, Finance)

**Requirement:** IT administration MUST be separate from business operations

```yaml
# Separate roles for SoD compliance:

# IT Administrator (Platform)
user: it.admin@worldwidebank.com
tenant_role: owner
permissions:
  - billing:manage
  - users:write
  - settings:manage
  - NO surveillance operations

# Chief Surveillance Officer (Business)
user: susan.martinez@worldwidebank.com
tenant_role: surveillance_chief
permissions:
  - communications:analyze
  - investigations:approve
  - alerts:escalate
  - NO billing access
  - NO user provisioning (read only)

# Compliance Officer (Independent Oversight)
user: thomas.anderson@worldwidebank.com
tenant_role: compliance_officer
permissions:
  - ALL resources: read, export
  - NO write/modify permissions
```

**Audit Trail:** Clear separation shows who performed IT vs business actions

### 4.2 Pattern B: SMEs / Non-Regulated

**Option:** Merge owner permissions into top business role for simplicity

```yaml
# Marketing Agency Owner (Combined)
user: owner@creativeedge.agency
tenant_role: agency_owner
permissions:
  # Business permissions
  - campaigns:write
  - social_posts:publish
  
  # PLUS Platform permissions
  - billing:manage
  - users:write
  - settings:manage
```

**Trade-off:** Simpler but doesn't meet SoD requirements

---

## 5. Permission Model

### 5.1 JSONB Permission Structure

```json
{
  "permissions": [
    {
      "resource": "communications",
      "actions": ["read", "analyze", "flag", "export", "archive"]
    },
    {
      "resource": "investigations",
      "actions": ["read", "create", "assign", "approve", "close", "export"]
    },
    {
      "resource": "users",
      "actions": ["read"]
    }
  ]
}
```

### 5.2 Permission Check Flow

```python
# Tenant-level permission check:
async def has_permission(user_id, resource, action, db):
    # 1. Get user's role
    user = await db.get(UserModel, user_id)
    role = await db.get(RoleTemplate, user.role_id)
    
    # 2. Check role's permissions (JSONB)
    for perm in role.permissions:
        if perm['resource'] == resource and action in perm['actions']:
            return True
    return False

# Team-level permission check:
async def check_team_permission(user_id, team_id, resource, action, db):
    # 1. Get user's team membership
    member = await get_team_member(user_id, team_id, db)
    if not member:
        return False
    
    # 2. Get team role definition
    team_role = await db.get(TeamRoleDefinition, member.team_role_id)
    
    # 3. Check team role's permissions (JSONB)
    for perm in team_role.permissions:
        if perm['resource'] == resource and action in perm['actions']:
            return True
    return False
```

---

## 6. Demo Use Cases

### 6.1 Bank Surveillance (Enterprise)

**Use Case:** Global bank with regional surveillance operations

**Structure:**
```
backend/scripts/b2b/use_cases/bank_surveillance/
├── resources.yaml                  # communications, investigations, alerts, surveillance_reports
├── tenant_roles.yaml               # surveillance_chief, regional_director, compliance_officer
├── team_roles.yaml                 # desk_surveillance_manager, senior_analyst, surveillance_analyst, junior_analyst
└── README.md
```

**Key Features:**
- 7-role hierarchy (CSO → Regional Director → Desk Manager → Analysts)
- Enterprise resources (investigations, alerts, compliance reporting)
- Separation of Duties (owner ≠ surveillance_chief ≠ compliance_officer)
- Team = Trading desk

**Seeding:**
```bash
make b2b-seed-roles USE_CASE=bank_surveillance
make b2b-invite f=scripts/b2b/demo_configs/bank_surveillance_demo.json
```

### 6.2 Marketing Agency (SME)

**Use Case:** Digital marketing agency managing client accounts

**Structure:**
```
backend/scripts/b2b/use_cases/marketing_agency/
├── resources.yaml                  # campaigns, social_posts, creative_assets, analytics_reports
├── tenant_roles.yaml               # agency_owner, agency_admin, account_director
├── team_roles.yaml                 # account_manager, creative_lead, specialist, content_contributor
└── README.md
```

**Key Features:**
- Simple hierarchy (Owner → Director → Manager → Specialist)
- Client-focused resources (campaigns, social posts, creative assets)
- Team = Client account

**Seeding:**
```bash
make b2b-seed-roles USE_CASE=marketing_agency
make b2b-invite f=scripts/b2b/demo_configs/marketing_agency_demo.json
```

### 6.3 Task Management (Generic)

**Use Case:** Standard SaaS project management

**Structure:**
```
backend/scripts/b2b/use_cases/task_management/
├── resources.yaml                  # projects, tasks, comments, rag_documents
├── tenant_roles.yaml               # [] (uses base owner/admin/member/viewer)
├── team_roles.yaml                 # [] (uses base team_manager/team_contributor/team_reader)
└── README.md
```

**Key Features:**
- Uses base platform roles (no custom roles)
- Generic resources (projects, tasks)
- Simple team structure

**Seeding:**
```bash
make b2b-seed-roles USE_CASE=task_management
make b2b-invite f=scripts/b2b/demo_configs/task_management_demo.json
```

---

## 7. Customization Workflow

### 7.1 For Production Clients

**Step 1: Choose base use case**
```bash
cp -r use_cases/marketing_agency/* domain/
```

**Step 2: Customize for client**
```yaml
# domain/resources.yaml
resources:
  - name: campaigns
    display_name: Marketing Campaigns
  
  - name: client_reports        # ← Client-specific
    display_name: Client Reports
    
  - name: roi_analytics         # ← Client-specific
    display_name: ROI Analytics
```

**Step 3: Seed customization**
```bash
make b2b-seed-roles  # No USE_CASE = loads domain/
```

### 7.2 Conditional Team Role Loading

**If `domain/team_roles.yaml` is empty:**
```yaml
# domain/team_roles.yaml
team_roles: []  # Use base team_manager, team_contributor, team_reader
```

**If `domain/team_roles.yaml` has custom roles:**
```yaml
# domain/team_roles.yaml
team_roles:
  - name: account_manager
    # ... custom definition
```
→ **Base team roles are SKIPPED** (no pollution!)

---

## 8. Makefile Commands

```bash
# Demo shortcuts:
make b2b-demo-bank              # Reset DB + seed bank RBAC (then create tenant via UI)
make b2b-demo-marketing         # Reset DB + seed marketing RBAC
make b2b-demo-task              # Reset DB + seed task management RBAC

# Create demo tenants:
make b2b-invite f=scripts/b2b/demo_configs/bank_surveillance_demo.json

# Granular control:
make b2b-seed-roles USE_CASE=bank_surveillance  # Just reseed RBAC
make reset-db USE_CASE=marketing_agency         # Full reset with specific RBAC
```

---

## 9. Quick Reference

| Concept | Storage | Example |
|---------|---------|---------|
| **Role Template** | `b2b.role_templates` | Global definition: `owner` with permissions JSONB |
| **Tenant Role Instance** | `b2b.roles` | Per-tenant: Worldwide Bank's `owner` role |
| **User Assignment** | `b2b.users.role_id` | susan.martinez → surveillance_chief role |
| **Team Role Definition** | `b2b.team_role_definitions` | `desk_surveillance_manager` with permissions JSONB |
| **Team Member Assignment** | `b2b.team_members.team_role_id` | john.doe → senior_analyst in US Equities Desk team |

---

## 10. See Also

- [B2B RBAC Concepts Guide](../guides/b2b-rbac-concepts.md) - Developer implementation guide
- [Authorization Architecture](../architecture/b2b/authorization.md) - Deep technical dive
- [Bank Surveillance Use Case](/home/neeraj/.gemini/antigravity/brain/08ab7912-d441-4df9-96a1-b63018c1569e/enterprise_sme_use_cases.md) - Enterprise example
