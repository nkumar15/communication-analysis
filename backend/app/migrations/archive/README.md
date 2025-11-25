# Archived Migration Files

This directory contains obsolete migration files that have been superseded by consolidated migrations.

## Archived Files

These migrations have been **consolidated** into the current migration files:

### Consolidated into `001_schema.sql`:
- `001_initial.sql` - Original tenants and users tables
- `003_tenant_activation.sql` - Activation workflow fields
- `004_invitations_table.sql` - Invitations table

### Consolidated into `002_rbac.sql`:
- `005_rbac_system.sql` - RBAC tables (roles, resources, actions, permissions)
- `006_rbac_seed_data.sql` - Seed data and functions for RBAC

### One-time migrations (already applied):
- `007_migrate_legacy_roles.sql` - Migrated existing users to RBAC roles
- `008_add_role_column.sql` - Added role column (now in schema)
- `009_cleanup_member_role.sql` - Cleaned up legacy role data

## Current Active Migrations

The migration runner now only processes these files in order:

1. `001_schema.sql` - Core schema (tenants, users, invitations)
2. `002_rbac.sql` - RBAC system with seed data
3. `003_farmers.sql` - Farmers domain table
4. `004_row_level_security.sql` - Row Level Security policies

## Important Notes

- **Do not delete** these archived files - they provide historical context
- **Do not run** these migrations - they are superseded by the consolidated versions
- For fresh database setup, only run the 4 current migrations listed above
