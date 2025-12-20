# B2C Personal Workspaces Product

Personal and team workspace management for individual users.

## Status: 🚧 In Development

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Personal Workspace | 🚧 | Auto-created on signup |
| Team Workspace | 🚧 | User-created collaborative spaces |
| Workspace Members | 🚧 | Invite others to your workspace |
| Subscriptions | 📋 | Stripe/Paddle integration |
| Usage Limits | 📋 | Per-workspace resource limits |

## Platforms

- **Web**: `frontend/src/modules/b2c/web/`
- **iOS**: `frontend/mobile-b2c/` (scaffold)
- **Android**: `frontend/mobile-b2c/` (scaffold)

## Backend

- **Service**: `backend/services/b2c/` (Port 8002)
- **Database Schema**: `b2c.*`

## Architecture

### Workspace Model

| Type | Description | Owner | Members |
|------|-------------|-------|---------|
| Personal | Auto-created on signup | Single user | None |
| Team | User-created | Creator | Multiple via invites |

### Database Schema

```
b2c.workspaces     → id, name, type, owner_id, subscription_tier, settings
b2c.users          → id, email, firebase_uid, display_name, default_workspace_id
b2c.workspace_members → workspace_id, user_id, role, joined_at
```

### RLS (Row-Level Security)

- Users see only workspaces they own or are members of
- Context set via `SET app.current_user_id`

## Implementation Roadmap

1. [ ] User registration with auto workspace creation
2. [ ] Workspace CRUD APIs
3. [ ] Team member invitations
4. [ ] Workspace switching in frontend
5. [ ] Subscription management (Stripe/Paddle)
6. [ ] Usage tracking and limits

## Code Locations

| Component | Location |
|-----------|----------|
| Models | `backend/services/b2c/models/` |
| Routers | `backend/services/b2c/routers/` |
| Frontend | `frontend/src/modules/b2c/` |
| Migration | `backend/migrations/014_create_b2c_tables.sql` |

## Related Docs

- [Development Guide](../guides/development.md)

