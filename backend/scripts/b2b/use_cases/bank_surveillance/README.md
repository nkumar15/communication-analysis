# Bank Surveillance Use Case (Enterprise)

Complete RBAC configuration for Global Bank Surveillance operations.

## Features

- **Hierarchical teams:** Global → Regional → Trading Desk
- **7 roles:** surveillance_chief, regional_director, compliance_officer, desk_surveillance_manager, senior_analyst, surveillance_analyst, junior_analyst
- **Resources:** communications, investigations, alerts, surveillance_reports
- **Advanced:** Supports Geographic Boundaries and Data Classification plugins

## Usage

```bash
# Load this use case
USE_CASE=bank_surveillance python scripts/b2b/seed_rbac.py

# To customize for production
cp -r use_cases/bank_surveillance/* domain/
# Edit domain/ files as needed
python scripts/b2b/seed_rbac.py
```

## Demo Pitch

"Enterprise-grade surveillance for global financial institutions with multi-region compliance"
