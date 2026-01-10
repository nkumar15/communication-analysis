# Marketing Agency Use Case (SME)

Complete RBAC configuration for Digital Marketing Agency managing multiple client accounts.

## Features

- **Teams = Client accounts:** Nike, Starbucks, Tesla, etc.
- **6 roles:** agency_owner, agency_admin, account_director, account_manager, creative_lead, specialist, content_contributor
- **Resources:** campaigns, social_posts, creative_assets, analytics_reports, client_communications
- **Simple:** Pure 2D RBAC, no plugins needed

## Usage
```bash
# 1. Reset DB and seed RBAC with marketing agency use case
make reset-db
make b2b-seed-roles USE_CASE=marketing_agency

# 2. Create demo tenant
make b2b-invite f=scripts/b2b/use_cases/marketing_agency/marketing_agency_demo.json

# 3. Demo is ready!
# - Domain: creativeedge.agency
# - Owner: jennifer.blake@creativeedge.agency
```

## Demo Configuration

**Fixed Tenant ID:** `c6f2ea50-92a5-51d3-b4e5-5d233111cafe`
- Ensures idempotency
- Consistent for automated testing

**Primary Persona:**
- **Name:** Jennifer Blake
- **Role:** Agency Owner & CEO
- **Context:** Digital marketing agency managing multiple client accounts

## Demo Pitch

"Simple, powerful collaboration for marketing agencies managing multiple client accounts"
