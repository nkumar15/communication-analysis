# Platform Admin Console

SaaS administration console for platform operators.

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Dashboard | ✅ | Global stats (tenants, users) |
| Tenant Management | ✅ | Create, list, search tenants |
| Tenant Onboarding | ✅ | Email activation workflow |
| Impersonation | ✅ | "Login As" for support |
| Audit Logs | ✅ | Platform action tracking |

## Platforms

- **Web Only**: `frontend/src/modules/platform/web/`

## Backend

- **Service**: `backend/services/platform/` (Port 8001)
- **Database Schema**: `platform.*`

## Access

- **Login**: `/platform-login`
- **Console**: `/super-admin/*`

## Security

- Separate Firebase tenant for platform admins
- Isolated from B2B/B2C customer data
- Should run on internal network in production

## Related Docs

- [Platform Admin Guide](../guides/platform-admin.md)
- [System Architecture](../architecture/shared/system-architecture.md)
