# Seeding Strategy

This document describes the seeding architecture for the multi-tenant SaaS platform.

---

## B2B Seeding Strategy

The B2B seeding architecture uses a foundation-overlay pattern to support both core platform features and domain-specific use cases.

### Directory Structure

```
backend/
├── modules/b2b/scripts/seeds/          # Foundation seeds
│   ├── foundation_actions.yaml
│   ├── foundation_resources.yaml
│   ├── foundation_saas_roles.yaml
│   ├── foundation_team_roles.yaml
│   ├── foundation_plugins.yaml
│   └── foundation_subscription_plans.yaml
│
└── modules/domains/b2b/{USE_CASE}/scripts/seeds/  # Domain overlays
    ├── overlay_actions.yaml            # Additive
    ├── overlay_resources.yaml          # Additive
    ├── overlay_team_roles.yaml         # Exclusive (replaces foundation)
    ├── overlay_plugins.yaml            # Additive
    ├── overlay_subscription_plans.yaml # Deep merge (optional)
    ├── demo_tenant.json                # Demo tenant config
    └── seed_meta.py                    # Domain-specific meta seeder
```

### File Naming Convention

| Prefix | Location | Behavior |
|--------|----------|----------|
| `foundation_` | `b2b/scripts/seeds/` | Always loaded first |
| `overlay_` | `domains/b2b/{USE_CASE}/` | Loaded when USE_CASE set |
| `demo_` | `domains/b2b/{USE_CASE}/` | Demo/dev data only |

### Merge Strategies

#### Additive (UNION)
- **Applies to:** Actions, Resources, Plugin Templates
- **Behavior:** Domain items added to foundation items
- **Example:** Foundation 10 resources + Domain 16 resources = 26 total

#### Exclusive (REPLACE)
- **Applies to:** Team Roles
- **Behavior:** If USE_CASE set, domain roles **replace** foundation roles
- **Rationale:** Domain roles are complete; foundation roles are fallback

#### Deep Merge
- **Applies to:** Subscription Plans, Plugin Templates
- **Rules:**
  - Lists → UNION (plugins merged)
  - Primitives → Overlay wins (limits override)
  - Nested objects → Recursive merge

#### Plugin Templates Pattern
- **Foundation (`foundation_plugins.yaml`):** Template data that gets **cloned per tenant**
  - `geographic_boundaries.default_regions` → Cloned to `b2b.geographic_regions`
  - `data_classification.sensitivity_levels` → Cloned to `b2b.sensitivity_levels`
  - `hierarchical_teams.org_tiers` → Cloned to `b2b.org_tiers`

- **Overlay (`overlay_plugins.yaml`):** Configuration + Instance data
  - **Configuration:** Plugin behavior settings (e.g., `enforce_strict`, `global_roles`)
  - **Instance Data:** Domain-specific seed data (e.g., `hierarchical_teams.seed_data`)

- **Merge Behavior:** Overlay deep-merges with foundation, preserving template data while adding configuration

### Makefile Targets

| Target | Description |
|--------|-------------|
| `seed-all` | Run all seeds (with optional USE_CASE) |
| `seed-demo` | Full demo: DB reset + seeds + tenant + meta |
| `b2b-seed-meta` | Seed domain-specific meta data |
| `b2b-demo-bank` | Shortcut for `seed-demo USE_CASE=bank_surveillance` |

### Usage Examples

```bash
# Generic platform demo (foundation team roles)
make seed-demo

# Bank surveillance demo (domain team roles + meta)
make seed-demo USE_CASE=bank_surveillance

# Shortcut for bank demo
make b2b-demo-bank

# Just run seeds (no DB reset, no tenant)
make seed-all USE_CASE=bank_surveillance
```

### Creating a New Domain

1. Create directory: `modules/domains/b2b/{new_domain}/scripts/seeds/`
2. Add required files:
   - `overlay_actions.yaml` - Domain actions
   - `overlay_resources.yaml` - Domain resources
   - `overlay_team_roles.yaml` - Domain team roles
   - `demo_tenant.json` - Demo tenant config
   - `seed_meta.py` - Meta data seeder (optional)
3. Add Makefile shortcut (optional):
   ```makefile
   b2b-demo-{domain}:
       @$(MAKE) seed-demo USE_CASE={domain}
   ```

---

## B2C Seeding Strategy

Coming soon.

---

## Platform Seeding Strategy

Coming soon.
