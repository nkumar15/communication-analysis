# User Profile

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Manage personal settings, security, and preferences |
| **Target Persona** | All Users |
| **Permission** | `me:read`, `me:write` |

## Features/Widgets

| Widget | Description | Data Source |
|--------|-------------|-------------|
| **Personal Info** | Name, Avatar, Email (Read-only) | `users` table |
| **Security** | Change Password, MFA Settings | Firebase Auth |
| **Notifications** | Email/Push preferences | `user_settings` |
| **Session Activity** | List of active sessions/devices | Audit logs |

## User Stories

- **As a User**, I want to change my password so that I can secure my account.
- **As a User**, I want to update my avatar so that my team recognizes me.

## UX Rules

- **Email Immutable**: Email cannot be changed here (requires Admin support or special flow).
- **MFA Challenge**: Changing password requires current password re-entry.

## Technical Implementation

See [API Reference](../technical/api.md#user-profile)
