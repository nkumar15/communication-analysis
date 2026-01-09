# Core SaaS Boilerplate (Universal)

**DO NOT MODIFY** these files unless changing the base boilerplate.

These files define the universal B2B SaaS foundation loaded for ALL deployments:

## Files

- **`actions.yaml`** - All possible RBAC actions (read, write, delete, etc.)
- **`saas_resources.yaml`** - Core SaaS resources (dashboard, users, teams, billing, etc.)
- **`saas_roles.yaml`** - Default tenant roles (owner, admin, member, viewer)
- **`team_roles_base.yaml`** - Universal team roles (team_manager, team_contributor, team_reader)

## Usage

These are automatically loaded by `seed_rbac.py` for every deployment.

To customize for a specific business domain, edit files in `../domain/` instead.
