# Authorization & RBAC Architecture

**Audience:** Backend Developers

This document details the **Role-Based Access Control (RBAC)** system, explaining how to protect endpoints, check permissions, manage roles, and configure the system for different business domains.

For **Authentication**, see [Authentication Architecture](./authentication.md).

---

## 📚 Core Components

### 1. Database Schema (`b2b` schema)
*   **`b2b.roles`**: Tenant-specific roles (e.g., Owner, Admin).
*   **`b2b.role_permissions`**: Mapping of Roles to Permissions (`resource` + `action`).
*   **`b2b.role_templates`**: Global templates used to seed roles for new tenants.
*   **`b2b.team_role_definitions`**: Team-level role definitions containing a JSONB `permissions` column.
*   **`b2b.resources`**: Universal resources (users, teams, billing, domain resources).
*   **`b2b.actions`**: Universal actions (read, write, delete, invite, export, manage).

### 2. Services
*   **`permission_checker.py`**: Functions for verifying `user_id + resource + action` (Tenant Level).
    *   **`has_permission(user_id, resource, action, db, role_id=None)`**: Check if user has tenant-level permission.
    *   **`get_user_permissions(user_id, db)`**: Get all permissions for a user.
*   **`TeamRoleService`**: CRUD for team-level role definitions.
*   **`scope_checker.py`**: Functions for hierarchical data access (Team vs Tenant scope).
    *   **`check_team_permission(user_id, team_id, resource, action, db, role_def_override=None)`**: Checks if user has permission within a specific team context.
    *   **`can_manage_team(user_id, team_id, db)`**: Checks for `team_members:manage` permission or `teams:write` tenant permission.
*   **`role_template_service`**: Manages role templates and seeds tenant roles during onboarding.

---

## 🔐 Protecting Endpoints

Use the decorators from `services.b2b.rbac.decorators` to secure API routes.

> [!NOTE]
> **Design Decision: Dependencies vs. Wrappers**
> We use FastAPI **Dependency Factories** (via `Depends()`) instead of standard Python reference decorators for three reasons:
> 1.  **OpenAPI Integration**: Permissions automatically appear in the Swagger documentation security scheme.
> 2.  **Dependency Injection**: Dependencies automatically receive the `db` session and `current_user` without complex argument inspection.
> 3.  **Testability**: Permissions can be easily mocked using `app.dependency_overrides` during testing.

### 1. Require Permission (Preferred)
Checks if the user's role has the specific capability.

```python
from modules.b2b.rbac.decorators import require_permission

@router.get("/projects")
async def list_projects(
    current_user: dict = require_permission('projects', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Only users with 'projects:read' permission can access.
    Owner/Admin have this by default.
    """
    pass
```

### 2. Require Role (Specific)
Checks for a specific named role. Use sparingly; prefer permissions for flexibility.

```python
from modules.b2b.rbac.decorators import require_role

@router.post("/invite")
async def invite_user(
    email: str,
    current_user: dict = require_role('admin', 'owner', 'team_manager')
):
    """Only admins or team managers can invite"""
    pass
```

### 3. Granular Team Scope (Resource Access)
For actions within a team (e.g., creating tasks), use `check_team_permission` inside the endpoint.

```python
from modules.b2b.rbac.scope_checker import check_team_permission

@router.post("/tasks")
async def create_task(
    data: TaskCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project(data.project_id, db)
    
    # Check if user's team role allows writing tasks
    if not await check_team_permission(current_user['id'], project.team_id, 'tasks', 'write', db):
        raise HTTPException(status_code=403, detail="Cannot create tasks in this team")
```

---

## 🔍 Data Scoping (RLS vs Application)

**1. Database Level (RLS)**
*   **Mechanism**: `SET LOCAL app.current_tenant_id`
*   **Effect**: Users strictly cannot see data from other tenants.

**2. Application Level (Team/User Scope)**
*   **Mechanism**: Functions in `scope_checker.py` module.
*   **Effect**: Filters data *within* the tenant (e.g., A user only sees their specific Team's tasks).

```python
from modules.b2b.rbac.scope_checker import get_accessible_user_ids

# Example: Get users I am allowed to see
accessible_ids = await get_accessible_user_ids(user_id, db)
query = select(UserModel).where(UserModel.id.in_(accessible_ids))
```

**Important:** RLS context is set **per-request** in the authentication middleware, not globally. This ensures thread safety and prevents cross-request data leakage.

---

## 🛡️ Tenant & User Access Control

### Platform Admin Controls

Platform administrators have super-admin capabilities to manage tenant lifecycle and access:

#### Tenant Deactivation

Platform admins can temporarily or permanently disable tenant access without deleting data.

**Use Cases:**
1. **Billing Issues** - Suspend access until payment is resolved
2. **Policy Violations** - Temporary suspension during investigation
3. **Security Incidents** - Immediate lockout for compromised tenants
4. **Voluntary Suspension** - Customer-requested pause (e.g., seasonal businesses)

**API Endpoints:**

```python
# Deactivate a tenant
PATCH /api/platform/b2b/tenants/{tenant_id}/deactivate
```

**Effect:**
- Sets `tenant.is_active = false`
- **All users** of that tenant receive `403 Forbidden` on next request
- Checked in `get_current_active_user` middleware (line 57-61 in b2b_auth.py):

```python
if not tenant.is_active:
    raise HTTPException(
        status_code=403,
        detail="This organization has been deactivated. Please contact your administrator."
    )
```

**Reactivation:**

```python
# Reactivate a tenant
PATCH /api/platform/b2b/tenants/{tenant_id}/reactivate
```

**Effect:**
- Sets `tenant.is_active = true`
- Users can immediately access the application again

**Data Preservation:**
- ✅ All data remains intact during deactivation
- ✅ No deletion or data loss
- ✅ Users, teams, projects, etc. all preserved
- ✅ Instant recovery on reactivation

#### User Deactivation

Tenant admins can deactivate individual users:

**Use Cases:**
1. **Employee Offboarding** - Disable access when staff leaves
2. **Security** - Block compromised user accounts
3. **Temporary Leave** - Pause access during leave of absence

**Effect:**
- Sets `user.is_active = false`
- User receives `401 Unauthorized` on login attempt
- Checked in middleware after user lookup

### Tenant Activation Status

Separate from deactivation, tenants have an activation lifecycle:

| State | Description | Access |
|-------|-------------|--------|
| `pending` | Created but owner hasn't activated | ❌ 403 Forbidden |
| `active` | Owner completed activation | ✅ Allowed (if is_active=true) |

**Validation in Middleware:**

```python
# Check activation status (line 50-54 in b2b_auth.py)
if tenant.activation_status != 'active':
    raise HTTPException(
        status_code=403,
        detail="Tenant is not yet activated. Please complete the activation process."
    )
```

---

## 📦 RBAC Seeding & Configuration

### How Roles Get Populated for Each Tenant

The RBAC system uses a **template-based seeding** approach where global role templates are copied to create tenant-specific roles during onboarding.

#### Database Tables

**Global Templates** (seeded once):
- `b2b.role_templates` - Blueprint roles (owner, admin, member, viewer)
- `b2b.resources` - Universal resources (users, teams, dashboard, billing, projects, tasks, etc.)
- `b2b.actions` - Universal actions (read, write, delete, invite, export, manage)
- `b2b.team_role_definitions` - Team role blueprints (team_manager, team_contributor, team_reader)

**Tenant-Specific** (created per tenant):
- `b2b.roles` - Actual roles for the tenant (copied from templates)
- `b2b.role_permissions` - Permission mappings (role_id + resource_id + action_id)

#### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RBAC SEEDING FLOW                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Global Seeding (Run Once)                                     │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ python scripts/b2b/seed_domain_data.py                    │         │
│  │                                                            │         │
│  │ Reads YAML files:                                        │         │
│  │  actions.yaml → b2b.actions                             │         │
│  │  resources.yaml → b2b.resources                         │         │
│  │  role_templates.yaml → b2b.role_templates               │         │
│  │  team_role_definitions.yaml → b2b.team_role_definitions │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                         │
│  STEP 2: Tenant Onboarding (Per Tenant)                                │
│  ┌───────────────────────────────────────────────────────────┐         │
│  │ python scripts/b2b/tenant_onboard.py create              │         │
│  │                                                            │         │
│  │ tenant_onboarding_service.onboard_tenant()                │         │
│  │   ├─ Create Firebase tenant                               │         │
│  │   ├─ Create DB tenant record                              │         │
│  │   ├─ Call role_template_service.seed_tenant_roles() ──┐  │         │
│  │   ├─ Create default team                               │  │         │
│  │   └─ Send activation email                             │  │         │ │  └───────────────────────────────────────────────────────────┘  │         │
│                                                             │  │         │
│  STEP 3: Role Seeding (Automated)                          │  │         │
│  ┌───────────────────────────────────────────────────────┐ │  │         │
│  │ seed_tenant_roles(tenant_id)                          │◄┘  │         │
│  │                                                        │    │         │
│  │ For each role template:                               │    │         │
│  │  1. Create role in b2b.roles (tenant-specific copy)   │    │         │
│  │  2. Parse template.permissions JSON                   │    │         │
│  │  3. For each {resource, actions[]}:                   │    │         │
│  │     - Lookup resource_id from b2b.resources           │    │         │
│  │     - Lookup action_id from b2b.actions               │    │         │
│  │     - Create row in b2b.role_permissions              │    │         │
│  └───────────────────────────────────────────────────────┘    │         │
│                                                                │         │
└────────────────────────────────────────────────────────────────────────┘
```

#### Step 1: Global Seeding (Run Once)

All RBAC configuration is defined in **YAML files** for easy editing:

**Location**: `backend/scripts/b2b/`

| File | Purpose |
|------|---------|
| `actions.yaml` | Universal actions (read, write, delete, invite, export, manage) |
| `resources.yaml` | SaaS boilerplate resources (dashboard, users, teams, billing, etc.) |
| `domain_resources.yaml` | Domain-specific resources (projects, tasks, comments) |
| `role_templates.yaml` | Tenant role templates with base permissions |
| `team_role_definitions.yaml` | Team role templates |
| `domain_role_permissions.yaml` | Domain permissions for tenant roles |
| `domain_team_permissions.yaml` | Domain permissions for team roles |

**Run the seed script**:
```bash
cd backend
python scripts/b2b/seed_domain_data.py
```

**Output**:
```
==============================================================
RBAC and Domain Data Seeding (From YAML)
==============================================================

Seeding 6 actions...
✓ Seeded 6 actions
Seeding 18 SaaS resources...
✓ Seeded 18 SaaS resources
Seeding 3 domain resources...
✓ Seeded 3 domain resources
Seeding 4 role templates...
  ✓ Created role template: owner
  ✓ Created role template: admin
  ✓ Created role template: member
  ✓ Created role template: viewer
✓ Processed 4 role templates
Seeding 3 team role definitions...
  ✓ Created team role: team_manager
  ✓ Created team role: team_contributor
  ✓ Created team role: team_reader
✓ Processed 3 team role definitions
Updating role templates with domain permissions...
  ✓ Updated owner with domain permissions
  ✓ Updated admin with domain permissions
  ✓ Updated member with domain permissions
  ✓ Updated viewer with domain permissions
✓ Role templates updated with domain permissions
Updating team roles with domain permissions...
  ✓ Updated team_manager with domain permissions
  ✓ Updated team_contributor with domain permissions
  ✓ Updated team_reader with domain permissions
✓ Team roles updated with domain permissions

✓ All changes committed successfully

==============================================================
✅ RBAC and domain data seeding complete!
==============================================================
```

This populates the global tables that are shared across all tenants.

#### Step 2: Tenant Onboarding

When creating a new tenant:
```bash
python scripts/b2b/tenant_onboard.py create \
  --company "Acme Corp" \
  --domain "acme.com" \
  --owner-email "admin@acme.com" \
  --oidc-provider "auth0" \
  --oidc-client-id "xxx" \
  --oidc-client-secret "yyy" \
  --oidc-issuer "https://acme.auth0.com/"
```

The `tenant_onboarding_service.onboard_tenant()` method automatically:

1. Creates Firebase tenant
2. Configures OIDC provider
3. Creates database tenant record
4. **Calls** `role_template_service.seed_tenant_roles(tenant_id)` ← **Roles created here!**
5. Creates default team
6. Creates owner invitation
7. Sends activation email

#### Step 3: Role Seeding Process

The `seed_tenant_roles()` method (implemented in `services/b2b/services/role_template_service.py`):

```python
async def seed_tenant_roles(self, db: AsyncSession, tenant_id: UUID) -> None:
    """Seeds default roles and permissions for a new tenant based on templates."""
    
    # 1. Fetch all Resources and Actions to map names to IDs
    resources = await self._get_resource_map(db)  # {name: UUID}
    actions = await self._get_action_map(db)      # {name: UUID}

    # 2. Fetch default templates from DB
    templates = await self._get_default_templates(db)

    for template in templates:
        # 3. Create tenant-specific Role
        role = await self._create_role(db, tenant_id, template)
        
        # 4. Assign Permissions (parse JSON → create role_permissions rows)
        await self._assign_permissions(db, role, template.permissions, resources, actions)
```

**Example Transformation**:

**Template** (`role_templates.yaml`):
```yaml
- name: admin
  display_name: Admin
  is_system_role: true
  is_default: true
  permissions:
    - resource: users
      actions: [read, write, invite]
    - resource: teams
      actions: [read, write, delete]
    - resource: projects
      actions: [read, write, delete]
```

**Becomes** (for Tenant `acme-uuid`):

`b2b.roles`:
```
┌─────────────┬─────────────┬────────┬───────────────┬─────────────────┐
│ id          │ tenant_id   │ name   │ display_name  │ is_system_role  │
├─────────────┼─────────────┼────────┼───────────────┼─────────────────┤
│ role-uuid-1 │ acme-uuid   │ admin  │ Admin         │ true            │
└─────────────┴─────────────┴────────┴───────────────┴─────────────────┘
```

`b2b.role_permissions`:
```
┌─────────────┬──────────────┬─────────────┐
│ role_id     │ resource_id  │ action_id   │  (Exploded from template JSON)
├─────────────┼──────────────┼─────────────┤
│ role-uuid-1 │ users-id     │ read-id     │  ← users: [read, write, invite]
│ role-uuid-1 │ users-id     │ write-id    │
│ role-uuid-1 │ users-id     │ invite-id   │
│ role-uuid-1 │ teams-id     │ read-id     │  ← teams: [read, write, delete]
│ role-uuid-1 │ teams-id     │ write-id    │
│ role-uuid-1 │ teams-id     │ delete-id   │
│ role-uuid-1 │ projects-id  │ read-id     │  ← projects: [read, write, delete]
│ role-uuid-1 │ projects-id  │ write-id    │
│ role-uuid-1 │ projects-id  │ delete-id   │
└─────────────┴──────────────┴─────────────┘
```

The JSON array in the template is **exploded** into individual relational rows in `role_permissions`, which makes querying efficient.

---

## 🎨 Customizing for Different Domains

The RBAC system is designed to support different business domains (e-commerce, healthcare, task management, etc.) by editing YAML configuration files.

### Example 1: E-Commerce Domain

#### Step 1: Define Domain Resources

Edit `backend/scripts/b2b/domain_resources.yaml`:

```yaml
# E-Commerce Domain Resources
resources:
  - name: products
    display_name: Product Catalog
    category: Domain
    description: Manage product listings and inventory
  
  - name: orders
    display_name: Order Management
    category: Domain
    description: Process and track customer orders
  
  - name: inventory
    display_name: Inventory
    category: Domain
    description: Stock management and warehousing
  
  - name: customers
    display_name: Customer Management
    category: Domain
    description: Customer profiles and purchase history
  
  - name: analytics
    display_name: Sales Analytics
    category: Domain
    description: Sales reports and business intelligence
```

#### Step 2: Define Tenant Role Permissions

Edit `backend/scripts/b2b/domain_role_permissions.yaml`:

```yaml
# E-Commerce permissions for tenant roles
domain_permissions:
  owner:
    - resource: products
      actions: [read, write, delete, export]
    - resource: orders
      actions: [read, write, delete, export]
    - resource: inventory
      actions: [read, write, manage]
    - resource: customers
      actions: [read, write, delete, export]
    - resource: analytics
      actions: [read, export]

  admin:
    - resource: products
      actions: [read, write, delete]
    - resource: orders
      actions: [read, write]
    - resource: inventory
      actions: [read, write]
    - resource: customers
      actions: [read, write]
    - resource: analytics
      actions: [read]

  member:
    - resource: products
      actions: [read, write]  # Can update product descriptions
    - resource: orders
      actions: [read, write]  # Can process orders
    - resource: inventory
      actions: [read]
    - resource: customers
      actions: [read]
    - resource: analytics
      actions: [read]

  viewer:
    - resource: products
      actions: [read]
    - resource: orders
      actions: [read]
    - resource: inventory
      actions: [read]
    - resource: customers
      actions: [read]
    - resource: analytics
      actions: [read]
```

#### Step 3: Customize Team Roles

Edit `backend/scripts/b2b/team_role_definitions.yaml` to use domain-specific names:

```yaml
team_roles:
  - name: team_manager
    display_name: Store Manager
    description: Manages store operations, inventory, and staff
    is_system: true
    permissions:
      - resource: team_members
        actions: [read, write, delete]
      - resource: team_settings
        actions: [read, write]

  - name: team_contributor
    display_name: Sales Associate
    description: Can process orders and update inventory
    is_system: true
    permissions:
      - resource: team_members
        actions: [read]
      - resource: team_settings
        actions: [read]

  - name: team_reader
    display_name: Inventory Viewer
    description: Read-only access to store operations
    is_system: true
    permissions:
      - resource: team_members
        actions: [read]
      - resource: team_settings
        actions: [read]
```

#### Step 4: Define Team Domain Permissions

Edit `backend/scripts/b2b/domain_team_permissions.yaml`:

```yaml
# E-Commerce team permissions
domain_permissions:
  team_manager:  # Store Manager
    - resource: products
      actions: [read, write, delete]
    - resource: orders
      actions: [read, write, delete]
    - resource: inventory
      actions: [read, write, manage]
    - resource: customers
      actions: [read, write]
    - resource: analytics
      actions: [read, export]

  team_contributor:  # Sales Associate
    - resource: products
      actions: [read, write]  # Can update product info
    - resource: orders
      actions: [read, write]  # Can process orders
    - resource: inventory
      actions: [read, write]  # Can update stock levels
    - resource: customers
      actions: [read]
    - resource: analytics
      actions: [read]

  team_reader:  # Inventory Viewer
    - resource: products
      actions: [read]
    - resource: orders
      actions: [read]
    - resource: inventory
      actions: [read]
    - resource: customers
      actions: [read]
    - resource: analytics
      actions: [read]
```

#### Step 5: Re-run Seed Script

```bash
cd backend
python scripts/b2b/seed_domain_data.py
```

The script is **idempotent** - it will:
- ✅ Add new resources
- ✅ Update existing role template permissions
- ✅ Update existing team role permissions
- ✅ Skip duplicates

#### Step 6: Handle Existing Tenants

**Important**: Existing tenants already have their roles seeded. New permissions won't automatically appear.

**Option 1: New Tenants Only** (Recommended for non-critical additions)
- New tenants automatically get updated permissions
- Existing tenants won't see new resources until manually granted

**Option 2: Manual Update via Admin UI**
- Go to Roles management
- Edit each role's permissions
- Add new resource permissions

**Option 3: Migration Script** (For production rollout)
```python
# scripts/b2b/migrate_existing_tenants.py
from services.b2b.services.role_template_service import role_template_service

async def update_all_tenants_with_new_permissions():
    """Add new domain permissions to existing tenants"""
    # Get all tenants
    tenants = await get_all_tenants(db)
    
    for tenant in tenants:
        # Get updated template
        template = await role_template_service.get_template_by_name(db, 'admin')
        
        # Get tenant's existing role
        admin_role = await get_role_by_name(db, tenant.id, 'admin')
        
        # Apply new permissions
        await role_template_service.assign_permissions_from_template(
            db, admin_role, template
        )
    
    await db.commit()
```

---

### Example 2: Healthcare Domain

```yaml
# domain_resources.yaml
resources:
  - name: patients
    display_name: Patient Records
    category: Domain
    description: Electronic health records and patient information
  
  - name: appointments
    display_name: Appointments
    category: Domain
    description: Schedule and manage patient appointments
  
  - name: medical_records
    display_name: Medical Records
    category: Domain
    description: Lab results, imaging, clinical notes
  
  - name: prescriptions
    display_name: Prescriptions
    category: Domain
    description: Medication orders and pharmacy management
  
  - name: billing_records
    display_name: Medical Billing
    category: Domain
    description: Insurance claims and payment processing

# team_role_definitions.yaml
team_roles:
  - name: team_manager
    display_name: Chief Physician
    description: Department head with full clinical and administrative access
    is_system: true
    permissions:
      - resource: team_members
        actions: [read, write, delete]
      - resource: team_settings
        actions: [read, write]
  
  - name: team_contributor
    display_name: Physician
    description: Can manage patients, write prescriptions, and update records
    is_system: true
    permissions:
      - resource: team_members
        actions: [read]
      - resource: team_settings
        actions: [read]
  
  - name: team_reader
    display_name: Nurse
    description: Can view records and appointments, limited editing
    is_system: true
    permissions:
      - resource: team_members
        actions: [read]
      - resource: team_settings
        actions: [read]

# domain_team_permissions.yaml
domain_permissions:
  team_manager:  # Chief Physician
    - resource: patients
      actions: [read, write, delete]
    - resource: appointments
      actions: [read, write, delete]
    - resource: medical_records
      actions: [read, write, delete]
    - resource: prescriptions
      actions: [read, write, delete]
    - resource: billing_records
      actions: [read, write]

  team_contributor:  # Physician
    - resource: patients
      actions: [read, write]
    - resource: appointments
      actions: [read, write]
    - resource: medical_records
      actions: [read, write]
    - resource: prescriptions
      actions: [read, write]  # Can prescribe
    - resource: billing_records
      actions: [read]  # Read-only

  team_reader:  # Nurse
    - resource: patients
      actions: [read, write]  # Can update vital signs
    - resource: appointments
      actions: [read, write]  # Can schedule
    - resource: medical_records
      actions: [read]  # Read-only
    - resource: prescriptions
      actions: [read]  # Read-only
    - resource: billing_records
      actions: [read]  # Read-only
```

---

## 🔑 Key Takeaways

### How It Works
1. **Role Templates** = Global blueprints in `b2b.role_templates`
2. **Roles** = Tenant-specific copies in `b2b.roles`
3. **Permissions** = Template's JSON exploded into `b2b.role_permissions` rows
4. **Automatic** = Happens during `tenant_onboarding_service.onboard_tenant()`
5. **Idempotent** = Safe to re-run seed script

### Configuration Philosophy
- **YAML-Driven** - All configuration in easily editable YAML files
- **Domain-Agnostic** - Core system works for any business domain
- **Layered Permissions** - Base + Domain permissions overlay
- **Version Controlled** - Clear diffs in git for permission changes
- **Separation of Concerns** - Schema (migrations) vs Data (YAML)

### Best Practices
1. **Start with templates** - Use base SaaS resources, add domain-specific later
2. **Iterate gradually** - Start with simple permissions, refine based on feedback
3. **Document changes** - Keep README.md updated with domain-specific logic
4. **Test thoroughly** - Verify permission checks work as expected
5. **Plan migrations** - Consider existing tenants when adding new resources

---

## 🚀 Extending Domain APIs (New Feature Guide)

When introducing a new domain feature (e.g., adding "Quotes" to an e-commerce system), follow these steps:

### Step 1: Add Resource to YAML

Edit `backend/scripts/b2b/domain_resources.yaml`:
```yaml
resources:
  # ... existing resources ...
  
  - name: quotes
    display_name: Sales Quotes
    category: Domain
    description: Generate and manage customer quotes
```

### Step 2: Add Permissions to Roles

Edit `backend/scripts/b2b/domain_role_permissions.yaml`:
```yaml
domain_permissions:
  owner:
    # ... existing permissions ...
    - resource: quotes
      actions: [read, write, delete, export]
  
  admin:
    - resource: quotes
      actions: [read, write, delete]
  
  member:
    - resource: quotes
      actions: [read, write]  # Can create quotes
  
  viewer:
    - resource: quotes
      actions: [read]
```

### Step 3: Add Team Permissions (if applicable)

Edit `backend/scripts/b2b/domain_team_permissions.yaml`:
```yaml
domain_permissions:
  team_manager:
    - resource: quotes
      actions: [read, write, delete, export]
  
  team_contributor:
    - resource: quotes
      actions: [read, write]
  
  team_reader:
    - resource: quotes
      actions: [read]
```

### Step 4: Re-run Seed Script

```bash
python scripts/b2b/seed_domain_data.py
```

### Step 5: Implement Protected Endpoints

Create your domain router using the new permission:

```python
# services/domains/quotes/router.py
from modules.b2b.rbac.decorators import require_permission

@router.get("/quotes")
async def list_quotes(
    current_user: dict = require_permission('quotes', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """List all quotes user has access to"""
    return await quote_service.list_quotes(db, current_user['id'])

@router.post("/quotes")
async def create_quote(
    data: QuoteCreate,
    current_user: dict = require_permission('quotes', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """Create a new quote"""
    return await quote_service.create_quote(db, current_user['id'], data)
```

### Step 6: Test Permissions

```python
# Test that member can create quotes
response = client.post("/quotes", json={"customer_id": "..."}, headers=member_auth)
assert response.status_code == 200

# Test that viewer cannot create quotes
response = client.post("/quotes", json={"customer_id": "..."}, headers=viewer_auth)
assert response.status_code == 403
```

---

## 🔧 Advanced Topics

### Custom Actions

If you need domain-specific actions beyond read/write/delete, add them to `actions.yaml`:

```yaml
actions:
  # ... existing actions ...
  
  - name: approve
    display_name: Approve
  
  - name: reject
    display_name: Reject
  
  - name: publish
    display_name: Publish
```

Then use in permissions:
```yaml
domain_permissions:
  admin:
    - resource: quotes
      actions: [read, write, approve, reject]
  
  member:
    - resource: quotes
      actions: [read, write]  # Cannot approve
```

### Dynamic Permissions

For user-specific or data-driven permissions (e.g., "can only edit own quotes"), implement in service layer:

```python
async def update_quote(db, user_id, quote_id, data):
    # Check base permission
    if not await has_permission(user_id, 'quotes', 'write', db):
        raise Forbidden()
    
    # Additional business rule
    quote = await get_quote(db, quote_id)
    if quote.created_by != user_id and not is_admin(user_id):
        raise Forbidden("Can only edit own quotes")
    
    # Proceed with update
```

---

## 🏗️ Role Management

### Role Templates (Seeding)
New tenants are automatically seeded with roles defined in `role_templates.yaml`.

*   **Standard Roles**: `owner`, `admin`, `member`, `viewer`
*   **Team Roles**: `team_manager`, `team_contributor`, `team_reader`

### Custom Roles
Tenants can create custom roles via the Admin UI or API, but they start from role templates during onboarding.

---

## 🔌 Plugin/Extension Architecture

**Audience:** Developers implementing enterprise features

The RBAC system features a **plugin architecture** that allows extending the core 2D RBAC model (Tenant Roles + Team Scope) with optional enterprise capabilities without modifying core code.

### Architecture Overview

The plugin system uses a **hook-based approach** where plugins register themselves and intercept permission checks at two points:

1. **Before Core Check** - Plugins can grant or deny permission before core RBAC evaluation
2. **After Core Check** - Plugins can augment or override the core RBAC decision

```python
┌──────────────────────────────────────────────────────────────┐
│                  Permission Check Flow                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Plugin Before Hooks                                      │
│     ├─ Geographic Boundaries Plugin                          │
│     ├─ Data Classification Plugin                            │
│     └─ Hierarchical Teams Plugin                             │
│                                                               │
│  2. Core RBAC Check                                          │
│     └─ has_permission(user, resource, action)                │
│                                                               │
│  3. Plugin After Hooks                                       │
│     ├─ Geographic Boundaries Plugin  ← Most common hook      │
│     ├─ Data Classification Plugin                            │
│     └─ ABAC Engine Plugin                                    │
│                                                               │
│  4. Return Final Decision                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Plugin Interface

All plugins implement the `RBACPlugin` base class:

```python
# core/rbac/plugin_system.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

class RBACPlugin(ABC):
    """Base class for all RBAC plugins"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin name, version, description"""
        pass
    
    @abstractmethod
    async def initialize(self, db: AsyncSession, config: Dict[str, Any]) -> bool:
        """Initialize plugin (run migrations, seed data)"""
        pass
    
    async def before_permission_check(
        self, 
        context: PermissionContext,
        db: AsyncSession
    ) -> Optional[bool]:
        """
        Hook called BEFORE core permission check
        Return:
          - True: Grant access immediately (skip core check)
          - False: Deny access immediately (skip core check)
          - None: Continue to core check
        """
        return None
    
    async def after_permission_check(
        self,
        context: PermissionContext,
        core_result: bool,
        db: AsyncSession
    ) -> bool:
        """
        Hook called AFTER core permission check
        Can augment or override core result
        """
        return core_result
    
    async def enrich_user_context(
        self,
        user: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Add plugin-specific data to user context"""
        return {}
```

### Plugin Registry

The `PluginRegistry` manages all registered plugins:

```python
# core/rbac/plugin_registry.py

class PluginRegistry:
    """Central registry for RBAC plugins"""
    
    def register(self, plugin: RBACPlugin):
        """Register a plugin"""
        pass
    
    async def check_permission(
        self,
        context: PermissionContext,
        core_permission_checker,
        db: AsyncSession
    ) -> bool:
        """Execute permission check with all plugins"""
        # 1. Before hooks
        for plugin in self._plugins:
            result = await plugin.before_permission_check(context, db)
            if result is not None:
                return result  # Short-circuit
        
        # 2. Core check
        core_result = await core_permission_checker(context, db)
        
        # 3. After hooks
        final_result = core_result
        for plugin in self._plugins:
            final_result = await plugin.after_permission_check(
                context, final_result, db
            )
        
        return final_result

# Global instance
plugin_registry = PluginRegistry()
```

### Available Enterprise Plugins

#### 1. Geographic Boundaries Plugin

**Purpose:** Enforce geographic/jurisdictional data access restrictions for multi-region compliance.

**Use Cases:**
- Banking surveillance (APAC/EMEA/Americas data segregation)
- GDPR compliance (EU data must stay with EU-scoped users)
- Data residency requirements (Singapore MAS, UK FCA)

**Database Schema:**
```sql
-- Plugin migration
CREATE TABLE b2b.geographic_regions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES b2b.tenants(id),
    code VARCHAR(10),  -- 'APAC', 'EMEA', 'AMER'
    name VARCHAR(100),
    regulatory_jurisdiction VARCHAR(50)  -- 'MAS', 'FCA', 'SEC'
);

ALTER TABLE b2b.users ADD COLUMN geographic_scopes UUID[];
ALTER TABLE b2b.communications ADD COLUMN data_region_id UUID;
```

**Implementation:**
```python
# plugins/geographic_boundaries/plugin.py

class GeographicBoundariesPlugin(RBACPlugin):
    async def after_permission_check(
        self, context, core_result, db
    ) -> bool:
        if not core_result:
            return False  # Core denied, don't override
        
        # Check if user role bypasses geographic restrictions
        if context.user['role']['name'] in self.config['global_roles']:
            return True
        
        # Get resource region
        resource_region = context.resource.data_region_id if context.resource else None
        if not resource_region:
            return True  # No geographic restriction
        
        # Check user's allowed regions
        user_scopes = context.user.get('geographic_scopes', [])
        if resource_region in user_scopes:
            return True
        
        # Deny: region mismatch
        logger.warning(
            f"Geographic boundary violation: user {context.user_id} "
            f"accessing region {resource_region}"
        )
        return False
```

**Configuration:**
```bash
# .env
RBAC_PLUGINS=geographic_boundaries

GEO_BOUNDARIES_STRICT=true
GEO_BOUNDARIES_GLOBAL_ROLES=owner,chief_surveillance_officer
```

#### 2. Hierarchical Teams Plugin

**Purpose:** Support nested team structures with inherited access.

**Use Cases:**
- Enterprise org charts (Region → Department → Team)
- Bank surveillance (Global → Regional → Desk → Unit)
- Multi-level sales organizations

**Database Schema:**
```sql
ALTER TABLE b2b.teams ADD COLUMN parent_team_id UUID REFERENCES b2b.teams(id);
ALTER TABLE b2b.teams ADD COLUMN team_type VARCHAR(50);
ALTER TABLE b2b.teams ADD COLUMN hierarchy_level INTEGER DEFAULT 0;

CREATE INDEX idx_teams_parent ON b2b.teams(parent_team_id);
```

**Implementation:**
```python
# plugins/hierarchical_teams/plugin.py

class HierarchicalTeamsPlugin(RBACPlugin):
    async def enrich_user_context(self, user: Dict[str, Any], db) -> Dict[str, Any]:
        """Add child teams to accessible teams"""
        direct_teams = await self._get_direct_teams(user['id'], db)
        
        # For managers, include child teams
        all_accessible = set(direct_teams)
        for team_id in direct_teams:
            if await self._is_team_manager(user['id'], team_id, db):
                children = await self._get_child_teams(team_id, db)
                all_accessible.update(children)
        
        return {"accessible_teams": list(all_accessible)}
```

#### 3. Data Classification Plugin

**Purpose:** Implement sensitivity-based access control with clearance levels.

**Use Cases:**
- Financial services (PUBLIC → CONFIDENTIAL → RESTRICTED)
- Healthcare (PHI protection levels)
- Government/Defense (security clearances)

**Database Schema:**
```sql
CREATE TYPE b2b.sensitivity_level AS ENUM (
    'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED', 'TOP_SECRET'
);

ALTER TABLE b2b.roles ADD COLUMN clearance_level INTEGER DEFAULT 1;
ALTER TABLE b2b.communications ADD COLUMN sensitivity sensitivity_level DEFAULT 'INTERNAL';
```

**Implementation:**
```python
# plugins/data_classification/plugin.py

class DataClassificationPlugin(RBACPlugin):
    SENSITIVITY_LEVELS = {
        'PUBLIC': 0,
        'INTERNAL': 1,
        'CONFIDENTIAL': 2,
        'RESTRICTED': 3,
        'TOP_SECRET': 4
    }
    
    async def after_permission_check(self, context, core_result, db) -> bool:
        if not core_result:
            return False
        
        # Get resource sensitivity
        sensitivity = context.resource.sensitivity if context.resource else None
        if not sensitivity:
            return True  # No classification
        
        # Check clearance
        user_clearance = context.user['role']['clearance_level']
        required_clearance = self.SENSITIVITY_LEVELS[sensitivity]
        
        return user_clearance >= required_clearance
```

### Enabling Plugins

**Step 1: Environment Configuration**
```bash
# .env
RBAC_PLUGINS=geographic_boundaries,hierarchical_teams,data_classification

# Plugin-specific config
GEO_BOUNDARIES_STRICT=true
HIERARCHICAL_TEAMS_MAX_DEPTH=5
DATA_CLASSIFICATION_DEFAULT=INTERNAL
```

**Step 2: Application Initialization**
```python
# backend/app.py

from core.rbac.plugin_registry import plugin_registry
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin
from plugins.data_classification.plugin import DataClassificationPlugin

async def initialize_rbac_plugins(db: AsyncSession):
    """Initialize RBAC plugins on startup"""
    
    plugin_config = {
        "geographic_boundaries": {
            "enforce_strict": True,
            "global_roles": ["owner"]
        },
        "hierarchical_teams": {"max_depth": 5},
        "data_classification": {"default_level": "INTERNAL"}
    }
    
    # Register plugins based on environment
    enabled_plugins = os.getenv("RBAC_PLUGINS", "").split(",")
    
    if "geographic_boundaries" in enabled_plugins:
        plugin_registry.register(GeographicBoundariesPlugin())
    
    if "hierarchical_teams" in enabled_plugins:
        plugin_registry.register(HierarchicalTeamsPlugin())
    
    if "data_classification" in enabled_plugins:
        plugin_registry.register(DataClassificationPlugin())
    
    # Initialize all
    await plugin_registry.initialize_all(db, plugin_config)
    
    logger.info(f"Initialized {len(plugin_registry.list_plugins())} RBAC plugins")
```

### Using Plugins in Code

Plugins integrate transparently with existing permission checks:

```python
# Standard check (core RBAC only)
if await has_permission(user_id, 'communications', 'read', db):
    # Access granted

# Plugin-aware check (recommended for enterprise)
if await has_permission_with_plugins(
    user_id,
    'communications',
    'read',
    db,
    resource_obj=communication  # Plugins can inspect resource
):
    # Access granted after core + plugin checks
```

**Modified Permission Checker:**
```python
# modules/b2b/rbac/permission_checker.py

from core.rbac.plugin_registry import plugin_registry, PermissionContext

async def has_permission_with_plugins(
    user_id: UUID,
    resource: str,
    action: str,
    db: AsyncSession,
    resource_obj: Optional[Any] = None
) -> bool:
    """Check permission with plugin support"""
    
    # Get user
    user = await db.get(User, user_id)
    if not user:
        return False
    
    # Build context
    context = PermissionContext(
        user_id=str(user_id),
        user=user.__dict__,
        resource_type=resource,
        resource=resource_obj,
        action=action,
        tenant_id=str(user.tenant_id)
    )
    
    # Execute with plugins
    async def core_check(ctx, db):
        return await has_permission(
            UUID(ctx.user_id), ctx.resource_type, ctx.action, db
        )
    
    return await plugin_registry.check_permission(context, core_check, db)
```

### Plugin Design Principles

**1. Non-Invasive**: Plugins don't modify core code, only extend it
**2. Composable**: Multiple plugins can be enabled simultaneously
**3. Opt-In**: Plugins are explicitly enabled via configuration
**4. Isolated**: Each plugin has its own schema migrations and dependencies
**5. Testable**: Plugins can be tested independently

### When to Use Plugins vs Core RBAC

**Use Core RBAC (No Plugins):**
- ✅ Standard permission model (who can do what)
- ✅ Team-based scoping is sufficient
- ✅ Flat organizational structure
- ✅ No compliance requirements

**Use Plugins:**
- ✅ Multi-region/multi-country operations
- ✅ Regulatory compliance (GDPR, HIPAA, SOC2)
- ✅ Complex organizational hierarchies
- ✅ Sensitivity-based access control
- ✅ Context-aware permissions

### Custom Plugin Development

Create custom plugins for domain-specific requirements:

```python
# plugins/custom_approval_workflow/plugin.py

class ApprovalWorkflowPlugin(RBACPlugin):
    """Require manager approval for sensitive actions"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="approval_workflow",
            version="1.0.0",
            description="Approval workflows for sensitive actions"
        )
    
    async def initialize(self, db, config):
        # Create approval tables
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS b2b.approval_requests (
                id UUID PRIMARY KEY,
                user_id UUID,
                resource_type VARCHAR(50),
                action VARCHAR(50),
                approved_by UUID,
                approved_at TIMESTAMP
            );
        """))
        return True
    
    async def before_permission_check(self, context, db):
        # Check if action requires approval
        if context.action in ['delete', 'export']:
            approval = await self._get_approval(context, db)
            if not approval:
                # Deny and require approval request
                return False
        return None  # Continue to core check
```

**See Also:**
- [Plugin Architecture Design](../../brain/rbac_plugin_architecture.md) - Complete technical specification
- [B2B RBAC Concepts Guide](../../guides/b2b-rbac-concepts.md) - Plugin usage guide

---

## Security Considerations
