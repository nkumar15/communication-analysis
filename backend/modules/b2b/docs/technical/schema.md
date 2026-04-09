# B2B Database Schema

**Schema**: `b2b`

## Identity & Access

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `tenants` | Tenant Configuration | `id`, `name`, `status`, `domain`, `oidc_config` |
| `users` | User Identity | `id`, `email`, `firebase_uid`, `tenant_id`, `role_id` |
| `roles` | Tenant Roles | `id`, `name`, `permissions` |
| `invitations` | Pending invites | `id`, `email`, `token`, `status`, `expires_at` |
| `bulk_invite_jobs` | Bulk Op Audit | `id`, `results`, `created_by` |

## Team Management

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `teams` | Organization Units | `id`, `tenant_id`, `name`, `parent_id` (Hierarchy) |
| `team_members` | User Assignments | `team_id`, `user_id`, `role` |

## Billing

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `subscriptions` | Active plans | `id`, `tenant_id`, `tier`, `current_period_end` |
| `invoices` | Billing records | `id`, `subscription_id`, `amount_due`, `status` |
| `coupons` | Discounts | `code`, `discount_type`, `amount` |

## Plugin Configuration

**Schema**: `tenant_settings`

| Table Name | Description | Key Columns |
| :--- | :--- | :--- |
| `enabled_plugins` | Active extensions | `tenant_id`, `plugin_name` |
| `plugin_config` | JSON Configuration | `tenant_id`, `plugin_name`, `config_json` |
