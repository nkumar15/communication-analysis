# Role-Based Access Control (RBAC) Guide

**Audience:** Developers and System Architects

This guide explains the RBAC implementation in the SSO boilerplate, including tenant roles, team roles, and permission management.

---

## Table of Contents

1. [Overview](#overview)
2. [Role Architecture](#role-architecture)
3. [Invitation Workflows](#invitation-workflows)
4. [Permission Model](#permission-model)
5. [Subscription & Billing Permissions](#subscription--billing-permissions)
6. [Best Practices](#best-practices)

---

## Overview

The system implements a **two-level role system**:

1. **Tenant Roles** - Organization-wide permissions (owner, admin, viewer)
2. **Team Roles** - Team-specific permissions (team_manager, team_member, team_viewer)

This pattern is used by GitHub, Slack, and Google Workspace for multi-tenant collaboration.

---

## Role Architecture

### Tenant Roles (Organization-Wide)

**Purpose:** Define what a user can do across the entire organization

**Examples:**
- `owner` - Full control over account, billing, and all features
- `admin` - Management capabilities (no billing/account deletion)
- `viewer` - Read-only access

**Storage:** `b2b.roles` table (per tenant)

**Assignment:** During user invitation

**Characteristics:**
- Every user has exactly ONE tenant role
- Persists across all teams
- Controls organization-level permissions (invite users, manage billing, etc.)

### Team Roles (Team-Specific)

**Purpose:** Define what a user can do within a specific team

**Examples:**
- `team_manager` - Can add/remove team members, edit team settings
- `team_member` - Active participant in team
- `team_viewer` - Read-only access to team

**Storage:** `b2b.team_members.team_role` column

**Assignment:** When adding user to a team

**Characteristics:**
- A user can have DIFFERENT roles in DIFFERENT teams
- Only applies within that team's context
- Does NOT override tenant-level permissions

---

## Invitation Workflows

### Standard Workflow

1. **Admin invites user** → Creates invitation with tenant role
2. **User receives email** → Clicks invitation link
3. **User completes SSO** → Authenticates via Firebase
4. **User joins tenant** → Account created with assigned role
5. **Optional: Auto-add to team** → If team specified, user added with team role

### Who Can Invite?

Only users with `users:invite` permission can invite new users:
- ✅ Owner
- ✅ Admin  
- ❌ Viewer (no permission)

### Enhanced Invitation (Optional Team Assignment)

When inviting a user, you can optionally:
- Select a team
- Select a team role

The user will be automatically added to that team upon accepting the invitation.

```json
{
  "email": "user@company.com",
  "role": "viewer",
  "team_id": "uuid-of-engineering-team",
  "team_role": "team_contributor"
}
```

**Result:**
- User created with tenant role = `viewer`
- User added to Engineering team with role = `team_contributor`

---

## Permission Model

### Permission Evaluation

Permissions are checked at two levels:

**1. Tenant-Level Permission:**
```python
if await has_permission(user_id, 'users', 'invite', db):
    # User can invite new users to organization
```

**2. Team-Level Permission:**
```python
if await can_manage_team(user_id, team_id, db):
    # User can manage this specific team
```

### RLS Context Requirements

> [!IMPORTANT]
> All permission checks require RLS (Row Level Security) context to be set BEFORE calling

The `has_permission()` function queries RLS-protected tables (`users`, `roles`). The middleware automatically sets this context, but if you're calling permission checks outside of a request handler, you must set it manually:

```python
# ✅ CORRECT: In route handler (middleware sets context automatically)
@router.get("/api/b2b/resources")
async def list_resources(
    current_user: dict = Depends(get_current_active_user),  # Sets RLS context
    db: AsyncSession = Depends(get_db)
):
    # Permission check works because RLS context is already set
    if not await has_permission(current_user['id'], 'resources', 'read', db):
        raise HTTPException(status_code=403)
    
    # Query resources
    result = await db.execute(select(Resource))
    return result.scalars().all()

# ✅ CORRECT: In background task (manual context setting)
async def process_batch(tenant_id: UUID, db: AsyncSession):
    from sqlalchemy import text
    
    # Must set context manually
    await db.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
    
    # Now permission checks work
    admin_result = await db.execute(
        select(User).join(Role).where(Role.name == 'admin')
    )
```

**See Also:**
- [Multi-Tenant Isolation Architecture](../architecture/b2b/multi-tenant-isolation.md) - Complete RLS documentation
- [B2B Authorization Architecture](../architecture/b2b/authorization.md) - Comprehensive RBAC implementation details

---

## Example Scenario

**User:** Alice  
**Tenant Role:** `admin`  
**Team Roles:**
  - Engineering: `team_manager`
  - Marketing: `team_viewer`

**Questions:**

**Q: Can Alice invite new users to the organization?**
- Check: `admin` role has `users:invite` permission?
- Answer: **YES** ✅

**Q: Can Alice add members to Engineering team?**
- Check 1: Tenant role `admin` has `teams:write`? **YES** ✅
- OR Check 2: Team role in Engineering = `team_manager`? **YES** ✅
- Answer: **YES** ✅

**Q: Can Alice add members to Marketing team?**
- Check 1: Tenant role `admin` has `teams:write`? **YES** ✅
- OR Check 2: Team role in Marketing = `team_viewer`? **NO** ❌
- Answer: **YES** ✅ (because of tenant role)

### Permission Hierarchy

**Tenant permissions > Team permissions**

If a user's tenant role grants a permission, team role cannot restrict it.

---

## Subscription & Billing Permissions

### Billing-Related Permissions

The system includes subscription and billing management with specific RBAC controls:

**Subscription Management:**
- `subscription:read` - View current subscription, plan details, seat count
- `subscription:write` - Upgrade/downgrade subscription tiers
- `subscription:manage` - Change payment modes, cancel subscription

**Invoice Management:**
- `invoices:read` - View billing history and invoices
- `invoices:write` - Mark invoices as paid (admin only)
- `invoices:export` - Download invoice PDFs

### Default Role Assignments

| Role | Subscription | Invoices | Billing Settings |
|------|-------------|----------|------------------|
| **Owner** | Full access | Full access | Full access |
| **Admin** | View, Upgrade | View, Export | View only |
| **Viewer** | View only | View only | No access |

**Example Use Cases:**

```python
# Check if user can upgrade subscription
if await has_permission(user_id, 'subscription', 'write', db):
    # User can initiate subscription upgrade
    await subscription_service.create_checkout_session(...)

# Check if user can view invoices
if await has_permission(user_id, 'invoices', 'read', db):
    # User can view billing history
    invoices = await invoice_service.list_invoices(...)
```

**See Also:** [B2B Subscription Architecture](../architecture/b2b/subscription.md) for complete billing implementation details.

---

## Plugin/Extension Architecture

**Audience:** Developers building enterprise features

The RBAC system is designed with a **plugin architecture** that keeps the core 2D RBAC (Tenant Roles + Team Scope) simple while allowing optional enterprise extensions for complex use cases.

### Why Plugins?

**Core Principle:** The 2D RBAC model serves 80% of use cases. For the remaining 20% (enterprise, regulated industries), plugins provide advanced capabilities without complicating the core.

**Example Scenarios:**
- **Multi-national banks** need geographic boundaries (APAC, EMEA, Americas) for data residency compliance
- **Healthcare systems** need data classification (PUBLIC, CONFIDENTIAL, HIPAA-PROTECTED) with clearance levels
- **Large enterprises** need hierarchical teams (Region → Department → Team) with inherited access

### Plugin System Overview

```
┌─────────────────────────────────────────────────────────────┐
│              CORE RBAC (Always Enabled)                     │
│  • Tenant Roles (Owner/Admin/Member/Viewer)                 │
│  • Team Scope (Manager/Member/Viewer)                       │
│  • Resource + Action Permissions                            │
│  • Extension Hooks (Plugin Registry)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ○ Plugin API
                        │
┌───────────────────────┴─────────────────────────────────────┐
│            Optional Enterprise Plugins                       │
│  • Geographic Boundaries                                     │
│  • Hierarchical Teams                                        │
│  • Data Classification                                       │
│  • ABAC (Attribute-Based Access Control)                     │
│  • Conditional Access (Time, Context, Approval Workflows)    │
└─────────────────────────────────────────────────────────────┘
```

### How Plugins Work

Plugins extend permission checks through **hooks**:

1. **Before Hook** - Execute before core permission check (can short-circuit)
2. **Core Check** - Standard RBAC permission validation
3. **After Hook** - Execute after core check (can augment or override result)

**Example Flow:**
```python
# User tries to access a communication record
has_access = await has_permission_with_plugins(
    user_id=user.id,
    resource="communications",
    action="read",
    resource_obj=communication
)

# 1. Before Hook: No plugin denies, continue
# 2. Core Check: User has "communications:read" permission ✓
# 3. After Hook: Geographic plugin checks region
#    - User has geographic_scopes = ["APAC"]
#    - Communication has data_region_id = "EMEA"
#    - Access DENIED (region mismatch)
```

### Available Plugins

#### 1. Geographic Boundaries Plugin

**Use Case:** Multi-region compliance (GDPR, MAS, SEC)

**Features:**
- Users have `geographic_scopes` (e.g., `['APAC', 'EMEA']`)
- Resources tagged with `data_region_id`
- Access denied if resource region not in user's scopes
- Global roles (e.g., CSO) can bypass restrictions

**Configuration:**
```bash
# .env
RBAC_PLUGINS=geographic_boundaries

GEO_BOUNDARIES_STRICT=true
GEO_BOUNDARIES_GLOBAL_ROLES=owner,chief_surveillance_officer
```

**Database Changes:**
```sql
-- Adds geographic_scopes to users
ALTER TABLE b2b.users ADD COLUMN geographic_scopes UUID[];

-- Adds data_region_id to resources
ALTER TABLE b2b.communications ADD COLUMN data_region_id UUID;
```

#### 2. Hierarchical Teams Plugin

**Use Case:** Enterprise org charts with nested teams

**Features:**
- Teams can have parent teams (Region → Desk → Unit)
- Managers inherit access to child team data
- Configurable depth limits
- Materialized view for performance

**Configuration:**
```bash
RBAC_PLUGINS=hierarchical_teams

HIERARCHICAL_TEAMS_MAX_DEPTH=5
```

**Database Changes:**
```sql
-- Adds hierarchy to teams
ALTER TABLE b2b.teams ADD COLUMN parent_team_id UUID;
ALTER TABLE b2b.teams ADD COLUMN hierarchy_level INTEGER;
```

#### 3. Data Classification Plugin

**Use Case:** Sensitivity-based access (finance, healthcare, legal)

**Features:**
- Resources have sensitivity levels (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, TOP_SECRET)
- Roles have clearance levels (0-4)
- Access denied if user's clearance < resource sensitivity
- Clearance requirements configurable per organization

**Configuration:**
```bash
RBAC_PLUGINS=data_classification

DATA_CLASSIFICATION_DEFAULT=INTERNAL
```

**Database Changes:**
```sql
-- Adds clearance to roles
ALTER TABLE b2b.roles ADD COLUMN clearance_level INTEGER;

-- Adds sensitivity to resources
CREATE TYPE b2b.sensitivity_level AS ENUM (
    'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', 'TOP_SECRET'
);
ALTER TABLE b2b.communications ADD COLUMN sensitivity sensitivity_level;
```

### Enabling Plugins

**Environment Configuration:**
```bash
# .env
RBAC_ENABLED=true

# Comma-separated list of plugins to enable
RBAC_PLUGINS=geographic_boundaries,hierarchical_teams,data_classification
```

**Application Startup:**
```python
# backend/app.py
from core.rbac.plugin_registry import plugin_registry
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin

async def initialize_plugins(db):
    # Register plugins
    plugin_registry.register(GeographicBoundariesPlugin())
    plugin_registry.register(HierarchicalTeamsPlugin())
    
    # Initialize all plugins
    await plugin_registry.initialize_all(db, plugin_config)
```

### Using Plugins in Code

Plugins are **transparent** - use standard permission checks:

```python
# Standard permission check (works with or without plugins)
if await has_permission(user_id, 'communications', 'read', db):
    # Access granted by core RBAC

# With plugin support (recommended for enterprise features)
if await has_permission_with_plugins(
    user_id,
    'communications',
    'read',
    db,
    resource_obj=communication  # Plugins can inspect resource
):
    # Access granted after core + plugin checks
```

**The difference:**
- `has_permission()` - Core RBAC only (tenant role + team scope)
- `has_permission_with_plugins()` - Core RBAC + enabled plugins

### Frontend Integration

Plugins enrich user context in `/auth/me` response:

```json
{
    "id": "...",
    "email": "analyst@bank.com",
    "role": "surveillance_analyst",
    "permissions": ["communications:read", "investigations:write"],
    
    // Plugin enrichments
    "geographic_scopes": ["apac", "emea"],  // Geographic plugin
    "clearance_level": 3,                    // Classification plugin
    "accessible_teams": ["team1", "team2", "child_team1"]  // Hierarchical plugin
}
```

### When to Use Plugins

**Use Core RBAC (No Plugins) When:**
- ✅ Simple permission model (who can do what)
- ✅ Team-based scoping is sufficient
- ✅ No geographic restrictions
- ✅ No compliance requirements for data classification
- ✅ Flat team structure

**Use Plugins When:**
- ✅ Multi-region/multi-country operations
- ✅ Regulatory compliance (GDPR, HIPAA, SOC2)
- ✅ Complex organizational hierarchies
- ✅ Sensitivity-based access control
- ✅ Context-aware permissions (time, location, device)
- ✅ Advanced approval workflows

### Custom Plugins

You can build custom plugins for domain-specific needs:

```python
# custom_plugins/industry_specific.py
from core.rbac.plugin_system import RBACPlugin, PluginMetadata

class CustomIndustryPlugin(RBACPlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_industry",
            version="1.0.0",
            description="Industry-specific access control"
        )
    
    async def after_permission_check(self, context, core_result, db):
        # Your custom logic here
        return core_result
```

**See Also:**
- [Advanced RBAC Plugin Architecture](../../brain/rbac_plugin_architecture.md) - Complete plugin system design
- [B2B Authorization Architecture](../architecture/b2b/authorization.md) - Detailed RBAC implementation

---

## Best Practices

### 1. Default Team Assignment

**Recommendation:** Auto-add new users to a default team

```python
# In invitation acceptance
default_team = await team_service.get_or_create_default_team(tenant_id)
await team_service.add_team_member(default_team.id, user.id, 'team_member')
```

### 2. Clear Role Naming

- Tenant roles: Owner, Admin, Viewer  
- Team roles: Team Manager, Team Member, Team Viewer

Prefix team roles with "Team" to avoid confusion.

### 3. Invitation Best Practices

**DO:**
- ✅ Default to lowest privilege role (viewer)
- ✅ Optionally assign to team during invitation
- ✅ Send clear invitation emails

**DON'T:**
- ❌ Allow viewers to invite users
- ❌ Default to admin role
- ❌ Skip email verification

### 4. Testing Checklist

When implementing RBAC:
- [ ] Test owner can invite all roles
- [ ] Test admin cannot invite owner
- [ ] Test viewer cannot invite anyone
- [ ] Test team manager can add to their team
- [ ] Test team viewer cannot add members
- [ ] Test auto-assignment to default team

---

## API Reference

### Invite User

```http
POST /api/b2b/invitations/invite
Content-Type: application/json
Authorization: Bearer {token}

{
  "email": "user@company.com",
  "role": "viewer",
  "team_id": "optional-team-uuid",
  "team_role": "team_contributor"
}
```

### Accept Invitation

```http
POST /api/b2b/invitations/join?token={invitation_token}
Authorization: Bearer {firebase_token}
```

### List Roles

```http
GET /api/b2b/roles
Authorization: Bearer {token}
```

### Get Team Roles

```http
GET /api/b2b/teams/team-roles
```

---

## Related Documentation

### User Guides
- [B2B Tenant Admin Guide](./b2b-tenant-admin.md) - How to use the admin interface
- [Development Guide](./development.md) - Setting up the development environment
- [Platform Admin Guide](./platform-admin.md) - Platform administration

### Architecture Documentation
- [B2B Authorization Architecture](../architecture/b2b/authorization.md) - Comprehensive RBAC system details
- [B2B Authentication](../architecture/b2b/authentication.md) - Auth flow and tenant validation
- [Multi-Tenant Isolation](../architecture/b2b/multi-tenant-isolation.md) - RLS implementation
- [B2B Subscription](../architecture/b2b/subscription.md) - Billing RBAC and payment flows
- [Tenant Onboarding Flow](../architecture/b2b/tenant-onboarding-flow.md) - Complete onboarding sequence

### Specifications
- [RBAC Specification](../specifications/rbac.md) - Functional requirements (SPEC-03)
- [User Management Specification](../specifications/user.md) - User workflows (SPEC-04)

### Testing
- [Test Matrix](../testing/test-matrix.md) - RBAC test coverage mapping

---

## FAQ

**Q: Can a user have multiple tenant roles?**
No. Each user has exactly one tenant role.

**Q: Can a user be in multiple teams?**
Yes. A user can be a member of multiple teams with different team roles in each.

**Q: Who manages team membership?**
- Owners and Admins (organization-wide permission)
- Team Managers (for their specific team)

**Q: Can team roles override tenant roles?**
No. Tenant-level permissions take precedence. If your tenant role grants access, team role cannot restrict it.

**Q: How do I add custom roles?**
Custom tenant roles can be created via the Role Management interface. Team roles are fixed in the boilerplate.
