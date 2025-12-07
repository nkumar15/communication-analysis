# Agriculture-Specific Deployment Notes

## Boilerplate Customization

This codebase is the **Agriculture Deployment** of the multi-tenant SSO boilerplate.

### Core System Roles (All Businesses)
- `owner` - Primary administrator
- `admin` - Administrator 
- `viewer` - Read-only user

### Agriculture-Specific Roles
- `role_name` - Manages resource_name 

These agriculture roles are marked as `is_default=True` and will be automatically seeded for all tenants.

## For Other Businesses

If adapting this codebase for a different industry:

1. **Edit** `backend/scripts/b2b/seed_domain_data.py`
2. **Replace** `projects` resource with your domain resource (e.g., `projects`)
3. **Replace** `field_manager` and `field_agent` templates with your business roles
4. **Keep** `is_default=True` for roles that are core to your business
5. **Run** `make b2b-seed-roles`

## Deployment Types

**Generic Boilerplate** (not this repo):
- Only owner, admin, viewer as defaults
- No domain-specific roles

**Agriculture Deployment** (this repo):
- owner, admin, viewer + field_manager, field_agent as defaults
- projects resource

**Retail Deployment** (hypothetical):
- owner, admin, viewer + store_manager, cashier as defaults  
- Products, inventory resources
