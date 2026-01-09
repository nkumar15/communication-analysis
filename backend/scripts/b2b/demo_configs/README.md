# Demo Tenant Configurations

This directory contains preset tenant configurations for demos and testing.

## Files

**Tenant Seed Configs:**
- `bank_surveillance_demo.json` - Enterprise bank surveillance demo
- `marketing_agency_demo.json` - SME marketing agency demo
- `task_management_demo.json` - Default task management demo (existing)

**Other:**
- `subscription_plans.yaml` - B2B subscription plans (Standard, Professional, Enterprise)

## Usage

### Create Demo Tenants

**Quick setup (default - task management):**
```bash
make b2b-invite
```

**Bank Surveillance Demo:**
```bash
make b2b-invite f=scripts/b2b/demo_configs/bank_surveillance_demo.json
# OR from within backend/scripts/b2b:
docker-compose exec -it b2b-api python /app/scripts/b2b/tenant_onboard.py create-local --file scripts/b2b/demo_configs/bank_surveillance_demo.json
```

**Marketing Agency Demo:**
```bash
make b2b-invite f=scripts/b2b/demo_configs/marketing_agency_demo.json
```

**Task Management Demo:**
```bash
make b2b-invite f=scripts/b2b/demo_configs/task_management_demo.json
```

### Complete Demo Setup Workflow

**For Bank Surveillance:**
```bash
# 1. Reset DB and seed RBAC with bank surveillance use case
make reset-db
make b2b-seed-roles USE_CASE=bank_surveillance

# 2. Create demo tenant
make b2b-invite f=scripts/b2b/demo_configs/bank_surveillance_demo.json

# 3. Demo is ready!
# - Domain: globalbank-surveillance.com
# - Owner: susan.martinez@globalbank-surveillance.com
# - Roles: surveillance_chief, regional_director, etc.
# - Resources: communications, investigations, alerts, reports
```

**For Marketing Agency:**
```bash
# 1. Reset DB and seed RBAC with marketing agency use case
make reset-db
make b2b-seed-roles USE_CASE=marketing_agency

# 2. Create demo tenant
make b2b-invite f=scripts/b2b/demo_configs/marketing_agency_demo.json

# 3. Demo is ready!
# - Domain: creativeedge.agency
# - Owner: jennifer.blake@creativeedge.agency
# - Roles: agency_owner, account_manager, specialist, etc.
# - Resources: campaigns, social_posts, creative_assets, etc.
```

## Fixed Tenant IDs

Each demo config has a **fixed UUID** for idempotency:

- **Bank Surveillance:** `b5e1fa40-89f4-50c2-a3f4-4c122000beef`
- **Marketing Agency:** `c6f2ea50-92a5-51d3-b4e5-5d233111cafe`
- **Task Management:** `05b51fa4-45f4-50c2-b3f4-4c122000347b`

This means:
- ✅ Running `create-local` multiple times is safe (idempotent)
- ✅ Same tenant ID every time for consistent testing
- ✅ Easy to reference in test scripts

## Demo Personas

**Bank Surveillance:**
- Susan Martinez - Chief Surveillance Officer (CSO)
- Domain: globalbank-surveillance.com
- Use case: Global bank surveillance, multi-region compliance

**Marketing Agency:**
- Jennifer Blake - Agency Owner & CEO
- Domain: creativeedge.agency
- Use case: Digital marketing agency managing client accounts

**Task Management:**
- Generic owner
- Domain: firstcompany.net
- Use case: Project/task management SaaS

## Customizing for New Clients

To create a new tenant config:

```json
{
  "tenant_id": "NEW-UUID-HERE",
  "firebase_tenant_id": "yourcompany-xyz123",
  "domain": "yourcompany.com",
  "company": "Your Company Name",
  "owner_email": "owner@yourcompany.com",
  "description": "Description of tenant",
  "use_case": "bank_surveillance|marketing_agency|task_management"
}
```

**Generate UUID:**
```bash
python3 -c "import uuid; print(uuid.uuid4())"
```

**Then load:**
```bash
make b2b-invite f=scripts/b2b/demo_configs/your_custom_tenant.json
```
