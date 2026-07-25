# Team Management

> **Status**: ![Status](https://img.shields.io/badge/Status-Complete-green)

Tools for organizing users, assigning roles, and managing invites.

## Quick Reference
- [Technical Spec (Invitations)](../technical/invitations.md)
- [Team Members Page](../pages/team_members.md)
- [API Reference](../technical/api.md#users-and-invitations)

## Overview
Enables Tenant Owners to scale their operations by inviting and organizing members.
- **Invitations**: Single email or Bulk CSV upload.
- **Hierarchy**: Organize users into nested Teams/Groups.
- **Member Directory**: Search and filtering capabilities.

## Workflows

### 1. Invite User
**Trigger**: Owner enters email on Team page.
**Process**:
1.  System generates unique token.
2.  Sends email via SMTP/SendGrid.
3.  User clicks link -> Redirects to Login/Signup.
**Output**: Pending Invitation -> Active User.

### 2. Bulk Action
**Trigger**: Owner uploads CSV.
**Process**: Async Job parses and validates each row, sending invites in background.
**Output**: `bulk_invite_jobs` record with results.

## Implementation Checklist
- [x] Invitation Token System
- [x] CSV Parser for Bulk Uploads
- [x] `team_members` hierarchy support
- [x] Email Notification integration

## Design Decisions
| Decision | Rationale |
| :--- | :--- |
| **Token-based Invites** | Secure; verifies email ownership. |
| **Async Bulk Jobs** | Prevents timeout on large CSV uploads. |
| **Hierarchical Teams** | Supports complex organizational structures (Region -> Branch -> Desk). |

## How to Implement

- [ ] **Define Roles**: Create granular permissions in `TeamRoleDefinition`.
- [ ] **Create Router**: Add endpoint `POST /invite` in `routers/invitations.py`.
- [ ] **Implement Service**: Logic for token usage in `services/invitation_service.py`.
