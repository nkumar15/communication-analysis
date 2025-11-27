# Platform Admin Configuration

## Overview

The platform admin uses a **completely separate login flow** from regular tenant users to avoid any mixing of authentication logic.

## Dynamic Configuration

Unlike the initial prototype, the platform admin login page now **dynamically fetches** the system tenant configuration from the backend. You do NOT need to hardcode tenant IDs or set environment variables for the frontend.

### How it works

1. Frontend calls `GET /api/platform/config` (public endpoint)
2. Backend looks up the tenant marked with `is_system_tenant = true`
3. Backend returns `{ firebase_tenant_id, oidc_provider_id }`
4. Frontend initializes Firebase login with these values

## Login Flows

### Regular Tenant Users
- URL: `http://localhost:3000/login`
- Flow:
  1. Enter email
  2. Backend resolves tenant from domain
  3. OIDC sign-in with tenant's provider
  4. Calls `/api/auth/sync-user`
  5. Redirects to `/dashboard`

### Platform Admins
- URL: `http://localhost:3000/platform-login`
- Flow:
  1. Page loads -> Fetches config from `/api/platform/config`
  2. User clicks "Login as Platform Admin"
  3. OIDC sign-in with system tenant provider
  4. **No sync-user call** - auth verified by `/api/platform/auth/me`
  5. Redirects to `/super-admin`

## Complete Separation

| Aspect | Tenant Users | Platform Admins |
|--------|--------------|-----------------|
| Login URL | `/login` | `/platform-login` |
| Login Component | `LoginPage.js` | `PlatformLogin.js` |
| Tenant Resolution | ✅ Dynamic via Domain | ✅ Dynamic via API |
| User Sync | `/api/auth/sync-user` | **NONE** |
| Auth Endpoint | `/api/auth/me` | `/api/platform/auth/me` |
| Route Guard | `ProtectedRoute` | `PlatformAdminRoute` |
| Dashboard | `/dashboard` | `/super-admin` |

## Setup Checklist

- [ ] Create system tenant in Firebase GCIP
- [ ] Configure OIDC provider for system tenant
- [ ] Run `make seed-system-tenant` (creates DB record with `is_system_tenant=true`)
- [ ] Run `make create-platform-admin EMAIL=admin@platform.net`
- [ ] Navigate to `http://localhost:3000/platform-login`
- [ ] Login with platform admin credentials
- [ ] Access `/super-admin` console

## Troubleshooting

**"System tenant configuration not found" error:**
- Ensure you ran `make seed-system-tenant`
- Check database: `SELECT * FROM tenants WHERE is_system_tenant = true;`

**401 Unauthorized:**
- User doesn't have `platform_admin` role in database
- Run `make create-platform-admin` to assign the role

**Duplicate users:**
- Should NOT happen with separate login pages
- If it does, check Network tab - `/api/auth/sync-user` should NEVER be called for platform admins
