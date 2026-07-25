# Scripts Directory

Utility scripts for managing the application.

## B2B Scripts

See [`b2b/README.md`](b2b/README.md) for details.

**Main scripts:**
- `b2b/seed_rbac.py` - Seed RBAC data (resources, actions, roles)
- `b2b/seed_subscription_plans.py` - Seed subscription tiers
- `b2b/tenant_onboard.py` - Create and onboard tenants

**Usage:**
```bash
# Default configuration
python scripts/b2b/seed_rbac.py

# Specific use case (bank_surveillance, marketing_agency, task_management)
USE_CASE=bank_surveillance python scripts/b2b/seed_rbac.py
```

## Testing with Use Cases

**Primary test use case: `bank_surveillance`**

Tests run against bank_surveillance because it has all features enabled.

See [b2b/README.md](b2b/README.md#testing) for testing policy.
