# Team Members & Invitations

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Manage tenant users, invitations, and role assignments |
| **Target Persona** | Admin / Tenant Owner |
| **Permission** | `users:read`, `users:invite`, `users:write` |

## Features/Widgets

| Widget | Description | Data Source |
|--------|-------------|-------------|
| **Member List** | Filterable table of users (Name, Email, Role, Status) | `users` table |
| **Invite Modal** | Single or Bulk (CSV) invitation form | `invitations` table |
| **Role Selector** | Dropdown to change user roles | `roles` table |
| **Bulk Status** | Progress of bulk invite jobs | `bulk_invite_jobs` |

## User Stories

- **As an Admin**, I want to list all users so that I can see who has access.
- **As an Admin**, I want to invite multiple users (CSV) so I can onboard teams efficiently.
- **As an Owner**, I want to deactivate a user so that they can no longer access the system.
- **As an Admin**, I want to see validation errors before sending bulk invites.

## UX Rules

- **Self-Demotion**: Prevent last Owner from demoting themselves.
- **Validation**: CSV upload must show specific row errors (e.g. "Row 5: Invalid Email").
- **Real-time Feedback**: Show progress bar for large bulk uploads.

## Bulk Invite CSV Format
- Required: `email`, `role` (owner, admin, member, viewer).
- Optional: `team_name`, `name`.
- Max 100 rows, 2MB file size.

## Technical Implementation

See [API Reference](../technical/api.md#users-and-invitations)
