# Base Layer

**Always loaded** - Core SaaS platform resources, actions, and roles.

## Files

| File | Purpose |
|------|---------|
| `actions.yaml` | Universal actions (read, write, delete, invite, export, manage) |
| `saas_resources.yaml` | Platform resources (dashboard, users, teams, billing, audit_logs) |
| `saas_roles.yaml` | Tenant-level roles (owner, admin, member, viewer) |
| `team_roles_fallback.yaml` | Team-level roles (used only if use case has no custom team roles) |

## Seeding Order

1. Actions (referenced by all permissions)
2. Resources (marked with `is_system_resource` flag)
3. SaaS Roles (tenant-level, with inline permissions)
4. Team Roles Fallback (only if use case's `team_roles.yaml` is empty)

## Team Roles: Fallback vs Use Case

```
Use Case has team_roles.yaml?
│
├── YES → Skip base/team_roles_fallback.yaml
│         Load use_cases/{name}/team_roles.yaml
│
└── NO  → Load base/team_roles_fallback.yaml
          (team_manager, team_contributor, team_reader)
```

This ensures no role pollution between generic and domain-specific roles.
