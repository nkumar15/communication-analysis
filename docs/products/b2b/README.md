# B2B Enterprise Product

Enterprise multi-tenant SaaS with team-based access control.

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Multi-Tenancy | ✅ | Isolated tenants with RLS |
| SSO/OIDC | ✅ | Auth0, Okta, Azure AD, Google |
| Teams | ✅ | Organize users into teams |
| RBAC | ✅ | Role-based permissions |
| Invitations | ✅ | Email-based user onboarding |
| Domain APIs | ✅ | Projects, Tasks, Comments |

## Platforms

- **Web**: `frontend/src/modules/b2b/web/`
- **iOS**: `frontend/mobile-b2b/ios/`
- **Android**: `frontend/mobile-b2b/android/`

## Backend

- **Service**: `backend/services/b2b/` (Port 8000)
- **Database Schema**: `b2b.*`

## Related Docs

- [Tenant Onboarding Flow](../architecture/b2b/tenant-onboarding-flow.md)
- [Domain APIs](../architecture/b2b/domain-apis.md)
- [Authentication](../architecture/b2b/authentication.md)
- [Authorization](../architecture/b2b/authorization.md)
- [Multi-Tenant Isolation](../architecture/shared/multi-tenant-isolation.md)
- [Tenant Admin Guide](../guides/b2b-tenant-admin.md)
- [RBAC Concepts](../guides/b2b-rbac-concepts.md)
