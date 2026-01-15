# RBAC Configuration - YAML Files

This directory contains YAML configuration files for RBAC (Role-Based Access Control) seeding. All data is now managed in easy-to-edit YAML files instead of SQL INSERT statements.

## Files Overview

### Core RBAC Data
- **`actions.yaml`** - Universal actions (read, write, delete, invite, export, manage)
- **`resources.yaml`** - SaaS boilerplate resources (dashboard, users, teams, billing, etc.)
- **`domain_resources.yaml`** - Domain-specific resources (projects, tasks, comments)

### Role Configurations
- **`role_templates.yaml`** - Default tenant-level roles (owner, admin, member, viewer)
- **`team_role_definitions.yaml`** - Default team-level roles (team_manager, team_contributor, team_reader)

### Domain Permissions
> [!NOTE]
> Permissions are now defined **inline** within role templates (in `role_templates.yaml` and `team_role_definitions.yaml`). Overlay files are no longer used.

## Usage

### Seeding RBAC Data

After running database migrations, execute the seed script:

```bash
# From backend directory
python scripts/b2b/seed_domain_data.py
```

The script will:
1. ✅ Seed actions from `actions.yaml`
2. ✅ Seed SaaS resources from `resources.yaml`
3. ✅ Seed domain resources from `domain_resources.yaml`
4. ✅ Create/update role templates from `role_templates.yaml` (includes inline permissions)
5. ✅ Create/update team role definitions from `team_role_definitions.yaml` (includes inline permissions)

### Modifying RBAC Configuration

**To add a new action:**
1. Edit `actions.yaml`
2. Run seed script (idempotent)

**To add a new resource:**
1. For SaaS features: Edit `resources.yaml`
2. For domain features: Edit `domain_resources.yaml`
3. Run seed script

**To modify role permissions:**
1. Edit `role_templates.yaml` or `team_role_definitions.yaml` directly (inline permissions)
2. Run seed script (updates existing roles)

## File Formats

### Actions Format
```yaml
actions:
  - name: read
    display_name: View
  - name: write
    display_name: Create/Edit
```

### Resources Format
```yaml
resources:
  - name: dashboard
    display_name: Dashboard
    category: Analytics
    description: Statistics, metrics, and overview
```

### Role Templates Format
```yaml
role_templates:
  - name: owner
    display_name: Owner
    description: Full administrator access
    is_system_role: true
    is_default: true
    permissions:
      - resource: dashboard
        actions: [read]
      - resource: users
        actions: [read, write, delete, invite]
```

### Team Role Definitions Format
```yaml
team_roles:
  - name: team_manager
    display_name: Team Manager
    description: Full team management
    is_system_role: true
    permissions:
      - resource: team_members
        actions: [read, write, delete]
```

### Domain Permissions Format
```yaml
domain_permissions:
  owner:
    - resource: projects
      actions: [read, write, delete]
  admin:
    - resource: projects
      actions: [read, write, delete]
```

## Migration from SQL

**Before:** INSERT statements in `migrations/004_b2b_rbac.sql` (~150 lines)  
**After:** YAML files (~200 lines, much more readable)

The migration SQL file now contains **only schema definitions** (CREATE TABLE, CREATE INDEX).  
All seed data has been moved to YAML files for easier editing and version control.

## Benefits

✅ **Readable** - YAML is easier to read and edit than SQL  
✅ **Maintainable** - Changes don't require SQL knowledge  
✅ **Version Controlled** - Clear diffs in git  
✅ **Idempotent** - Safe to run multiple times  
✅ **Separation** - Schema (migrations) vs Data (YAML)  
✅ **Flexible** - Easy to customize per deployment

## Customization for Different Domains

**For E-commerce:**
```yaml
# domain_resources.yaml
resources:
  - name: products
    display_name: Products
    category: Domain
  - name: orders
    display_name: Orders
    category: Domain
  - name: inventory
    display_name: Inventory
    category: Domain
```

**For Healthcare:**
```yaml
# domain_resources.yaml
resources:
  - name: patients
    display_name: Patients
    category: Domain
  - name: appointments
    display_name: Appointments
    category: Domain
  - name: medical_records
    display_name: Medical Records
    category: Domain
```

Simply edit the YAML files and run the seed script!
