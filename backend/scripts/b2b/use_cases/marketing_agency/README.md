# Marketing Agency Use Case (SME)

Complete RBAC configuration for Digital Marketing Agency managing multiple client accounts.

## Features

- **Teams = Client accounts:** Nike, Starbucks, Tesla, etc.
- **6 roles:** agency_owner, agency_admin, account_director, account_manager, creative_lead, specialist, content_contributor
- **Resources:** campaigns, social_posts, creative_assets, analytics_reports, client_communications
- **Simple:** Pure 2D RBAC, no plugins needed

## Usage

```bash
# Load this use case
USE_CASE=marketing_agency python scripts/b2b/seed_rbac.py

# To customize for production
cp -r use_cases/marketing_agency/* domain/
# Edit domain/ files as needed
python scripts/b2b/seed_rbac.py
```

## Demo Pitch

"Simple, powerful collaboration for marketing agencies managing multiple client accounts"
