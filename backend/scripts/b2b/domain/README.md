# Domain Configuration (Customizable)

**START HERE** to customize for your business domain!

## Files

Edit these files to add your business-specific resources and roles:

1. **`resources.yaml`** - Your business resources (products, orders, patients, etc.) **← START HERE!**
2. **`tenant_permissions.yaml`** - Add permissions to existing tenant roles
3. **`team_permissions.yaml`** - Add permissions to existing team roles
4. **`tenant_roles.yaml`** (optional) - Add custom tenant-level roles
5. **`team_roles.yaml`** (optional) - Add custom team-level roles

## Examples

**E-commerce:**
```yaml
resources:
  - name: products
    display_name: Products
  - name: orders
    display_name: Orders
```

**Healthcare:**
```yaml
resources:
  - name: patients
    display_name: Patients
  - name: appointments
    display_name: Appointments
```

## Quick Start

**From scratch:**
1. Edit `resources.yaml` - add your business resources
2.Edit `tenant_permissions.yaml` - give owner/admin access to those resources
3. Run: `python scripts/b2b/seed_rbac.py`

**From a demo:**
```bash
# Copy use case to domain
cp -r use_cases/marketing_agency/* domain/

# Customize as needed
nano domain/resources.yaml

# Seed database
python scripts/b2b/seed_rbac.py
```
