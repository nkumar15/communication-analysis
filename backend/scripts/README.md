# Scripts Directory

This directory contains utility scripts for managing the application.

## Domain Data Seeding

### `seed_domain_data.py`

Seeds domain-specific resources and role templates that are unique to your business.

**Purpose**: Separates domain-specific data (e.g., shops) from core boilerplate data (users, roles, tenants) to make the codebase reusable for different businesses.

**What it seeds**:
- Domain resources (e.g., `shops`)
- Domain role templates (e.g., `shop_manager`, `shop_agent`)

**Usage**:
```bash
# Via Makefile (recommended)
make seed-domain

# Or directly
docker-compose run --rm b2b-api python scripts/seed_domain_data.py
```

**When to run**:
- After initial `make migrate`
- When adding new domain resources
- When setting up a new environment

**Customization**:
To adapt this boilerplate for a different business:
1. Edit `scripts/seed_domain_data.py`
2. Replace domain resources with your business-specific ones
3. Update role templates as needed
4. Run `make seed-domain`

**Idempotent**: Safe to run multiple times - checks if data already exists before seeding.

## Full Setup Flow

```bash
# 1. Setup environment
make setup

# 2. Start services
make up

# 3. Run core migrations (users, roles, tenants)
make migrate

# 4. Seed domain data (shops, etc.)
make seed-domain

# Done! Your app is ready
```
