# Authorization & RBAC Architecture

**Audience:** Backend Developers  
**Last Updated:** 2026-01-09

This document details the **Role-Based Access Control (RBAC)** system implementation, including configuration architecture, seeding process, permission checks, and customization workflows.

For **Authentication**, see [Authentication Architecture](./authentication.md).

---

## 📋 Table of Contents

1. [Configuration Architecture](#configuration-architecture)
2. [Database Schema](#database-schema)
3. [Seeding Process](#seeding-process)
4. [Permission System](#permission-system)
5. [Endpoint Protection](#endpoint-protection)
6. [Data Scoping](#data-scoping)
7. [Separation of Duties](#separation-of-duties)

---

## 🏗️ Configuration Architecture

### Directory Structure

The RBAC system uses a layered configuration approach:

```
backend/scripts/b2b/
├── core/                           # Universal SaaS boilerplate
│   ├── actions.yaml                # Universal actions (read, write, etc.)
│   ├── saas_roles.yaml             # Platform roles (owner, admin, member, viewer)
│   ├── saas_resources.yaml         # Platform resources (users, teams, billing)
│   ├── team_roles_base.yaml        # Generic team roles
│   └── README.md
│
├── domain/                         # Production customization
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
├── seed_rbac.py                    # Main seeding script
└── tenant_onboard.py
```

### Configuration Loading

**Development/Demo (with USE_CASE):**
```bash
USE_CASE=bank_surveillance python seed_rbac.py
# Loads: core/* + use_cases/bank_surveillance/*
```

**Production (without USE_CASE):**
```bash
python seed_rbac.py
# Loads: core/* + domain/*
```

**Loading Priority:**
1. Always: `core/` (actions, saas_roles, saas_resources)
2. Conditionally: `use_cases/<USE_CASE>/` OR `domain/`
3. Smart: Base team roles **skipped** if custom team roles defined

---

## 💾 Database Schema

### Three-Table Role Model

```sql
-- 1. Global Role Templates (Blueprints)
CREATE TABLE b2b.role_templates (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    is_system_role BOOLEAN,
    is_default BOOLEAN,
    permissions JSONB NOT NULL  -- [{"resource":"users","actions":["read","write"]}]
);

-- 2. Tenant-Specific Role Instances
CREATE TABLE b2b.roles (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    name VARCHAR(50),
    display_name VARCHAR(100),
    is_system_role BOOLEAN,
    is_active BOOLEAN,
    UNIQUE(tenant_id, name)
);

-- 3. User Role Assignments
CREATE TABLE b2b.users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    role_id UUID REFERENCES b2b.roles(id),  -- User's assigned role
    ...
);
```

### Data Flow

```
SEED PHASE:
    YAML files → role_templates (global)

TENANT CREATION:
    role_templates → roles (per-tenant instances)

USER INVITATION:
    roles → users.role_id (user assignment)
```

---

## 🌱 Seeding Process

### seed_rbac.py Architecture

```python
# Key functions:
async def seed_actions(db)              # Load core/actions.yaml
async def seed_saas_resources(db)       # Load core/saas_resources.yaml
async def seed_saas_roles(db)           # Load core/saas_roles.yaml → role_templates
async def seed_base_team_roles(db)      # Load core/team_roles_base.yaml (conditional)
async def seed_domain_resources(db)     # Load CONFIG_DIR/resources.yaml
async def seed_additional_tenant_roles(db)  # Load CONFIG_DIR/tenant_roles.yaml
async def seed_additional_team_roles(db)     # Load CONFIG_DIR/team_roles.yaml
```

### Conditional Team Role Loading

**Key Logic:**
```python
async def seed_base_team_roles(db):
    # Check if use case defines custom team roles
    use_case_team_roles_data = load_yaml(CONFIG_DIR / 'team_roles.yaml')
    use_case_team_roles = use_case_team_roles_data.get('team_roles', [])
    
    if use_case_team_roles:
        # Skip base roles to prevent pollution
        print("✓ Skipping base team roles (use case defines custom team roles)")
        return
    
    # Load base team roles from core/
    ...
```

---

## 🏛️ Separation of Duties (SoD)

### Pattern A: Regulated Industries

**Required for:** Banks, Healthcare, Finance (SOX, MiFID II, FINRA compliance)

**Implementation:**
```yaml
# Separate IT and Business roles

# IT Administrator (Platform)
owner:
  permissions:
    - billing:manage
    - users:write
    - settings:manage
    # NO business operations

# Chief Surveillance Officer (Business)
surveillance_chief:
  permissions:
    - communications:analyze
    - investigations:approve
    - alerts:escalate
    # NO billing
    # NO user provisioning (read only)

# Independent Compliance Officer
compliance_officer:
  permissions:
    - ALL resources: read, export
    # NO write permissions
```

---

## 🔄 Use Case Examples

### Bank Surveillance
For a deep dive into the Enterprise Bank Surveillance RBAC implementation (Hybrid Model, SoD, Chinese Walls), please see the dedicated guide:

👉 **[Bank Surveillance Use Case README](/home/neeraj/codes/enterprisesso/backend/scripts/b2b/use_cases/bank_surveillance/README.md)**

### Marketing Agency

**Configuration:**
```bash
USE_CASE=marketing_agency python seed_rbac.py
```

**Roles Seeded:**
- Tenant: `owner`, `admin`, `agency_owner`, `account_director`
- Team: `account_manager`, `creative_lead`, `specialist`, `content_contributor`

---

## 📖 See Also

- [RBAC Specification](../../specifications/b2b/rbac.md)
- [RBAC Concepts Guide](../../guides/b2b-rbac-concepts.md)
- [Enterprise Use Cases](/home/neeraj/.gemini/antigravity/brain/08ab7912-d441-4df9-96a1-b63018c1569e/enterprise_sme_use_cases.md)
