# Tenant Onboarding

## Overview

| Attribute | Details |
|-----------|---------|
| **Goal** | Provision and activate new Tenants via invitation |
| **Target Persona** | Platform Admin (Inviter), Tenant Owner (Invitee) |
| **Permission** | `platform:admin` (to invite), Public (to activate) |

## Features/Widgets

| Widget | Description | Data Source |
|--------|-------------|-------------|
| **Invite Tenant Form** | Admin form to invite new org (Name, Owner Email) | `tenants` table |
| **Activation Landing** | Public page to set password/SSO after email click | `users` (create owner) |
| **Deep Link Handler** | Mobile app handler for activation links | Universal Links |

## User Stories

- **As a Platform Admin**, I want to invite a company (Tenant) so that I can control who joins.
- **As a Tenant Owner**, I want to click a secure email link to activate my account.

## UX Rules

- **Expiry**: Links expire in 48 hours. Show "Link Expired" page if late.
- **Idempotency**: Clicking link twice should show "Already Activated" or redirect to Login.
- **Mobile First**: If app is installed, activation link should open App.

## Activation Flow
1. Admin POSTs `/tenants` (Invite).
2. Tenant gets Email.
3. Tenant clicks Link -> `GET /activate/validate`.
4. Tenant sets Password -> `POST /activate`.
5. Tenant is Active and logged in.

## Technical Implementation

See [API Reference](../technical/api.md#tenant-onboarding)
