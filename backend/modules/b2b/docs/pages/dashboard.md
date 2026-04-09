# Dashboard

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Provide role-appropriate views for all users |
| **Target Persona** | All (Owner, Admin, Member) |
| **Permission** | `dashboard:read` |

## Features/Widgets

| Widget | Description | Data Source |
|--------|-------------|-------------|
| **Org Health** | Active users, recent activity (Owner only) | `users`, `audit_logs` |
| **Pending Invites** | List of pending invitations (Admin/Owner) | `invitations` |
| **My Teams** | List of teams the user belongs to | `team_members` |
| **My Tasks** | Assigned tasks across projects | `tasks` |

## User Stories

- **As an Owner**, I want an Billing & Health overview.
- **As an Admin**, I want to see pending User Invites.
- **As a Member**, I want to see **My Teams** and **My Tasks**.

## UX Rules

- **Progressive Disclosure**: Members should NOT see Billing or Org Health.
- **Empty States**: If a user has no tasks, show "Create your first task" CTA.
- **Loading**: Show skeleton loaders for specific widgets.

## Technical Implementation

See [API Reference](../technical/api.md#dashboard)
