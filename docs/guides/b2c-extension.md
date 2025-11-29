# B2C Extension Guide

## Overview

The B2C module provides a skeleton structure for implementing personal and team workspace functionality. This guide explains how to extend it for your needs.

## Architecture

### Workspace Model

**Personal Workspace:**
- Created automatically when a user signs up
- `workspace_type = 'personal'`
- Single user (owner)
- Free tier by default

**Team Workspace:**
- Created manually by users
- `workspace_type = 'team'`
- Multiple members via `workspace_members` table
- Paid subscription tiers

### Database Schema (`b2c` schema)

```
workspaces
├── id (UUID)
├── name
├── type ('personal' | 'team')
├── owner_id (UUID)
├── subscription_tier
└── settings (JSONB)

users
├── id (UUID)
├── email
├── firebase_uid
├── display_name
└── default_workspace_id

workspace_members
├── workspace_id (UUID)
├── user_id (UUID)
├── role ('owner' | 'admin' | 'member')
└── joined_at
```

## Extending the B2C Module

### 1. Implement Authentication

Update `services/b2c/routers/auth.py`:
- User registration → Auto-create personal workspace
- Login → Set workspace context
- Workspace switching

### 2. Implement Workspace Management

Update `services/b2c/routers/workspaces.py`:
- **List workspaces:** Query workspaces user owns or is a member of
- **Create workspace:** Create team workspace
- **Delete workspace:** Only owner can delete
- **Update workspace:** Name, settings, subscription

### 3. Implement Team Management

Create `services/b2c/routers/teams.py`:
- Invite members (email invitations)
- Remove members
- Update member roles
- List team members

### 4. Implement Subscription Management

Create `services/b2c/routers/subscriptions.py`:
- Integrate with Stripe/Paddle
- Upgrade/downgrade workspace
- Billing management
- Usage limits enforcement

### 5. Row-Level Security (RLS)

RLS policies are already in place:
- Users can only see workspaces they own or are members of
- Members can only see other members of their workspaces
- Users can only see their own profile

Set the current user context in your middleware:
```python
await conn.execute("SET app.current_user_id = $1", str(user_id))
```

### 6. Frontend Implementation

Extend `frontend/src/modules/b2c/`:

**Pages to implement:**
- `pages/WorkspaceDashboard.js` - Main workspace view
- `pages/WorkspaceSettings.js` - Workspace configuration
- `pages/TeamManagement.js` - Member management
- `pages/SubscriptionPage.js` - Billing & plans

**Components to create:**
- `components/WorkspaceSelector.js` - Dropdown to switch workspaces
- `components/SubscriptionCard.js` - Current plan display
- `components/MemberList.js` - Team members
- `components/InviteMemberModal.js` - Invitation flow

**Layout:**
- `layouts/WorkspaceLayout.js` - Common layout with workspace selector

## Example: Implementing Workspace Listing

### Backend (`services/b2c/routers/workspaces.py`)

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from core.middleware import get_current_user
from services.b2c.models import Workspace, WorkspaceMember
from services.b2c.schemas import WorkspaceResponse

@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Set RLS context
    await db.execute(
        "SET app.current_user_id = :user_id",
        {"user_id": str(current_user.id)}
    )
    
    # Query workspaces (RLS automatically filters)
    result = await db.execute(
        select(Workspace).order_by(Workspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    
    return workspaces
```

### Frontend (`modules/b2c/pages/WorkspaceDashboard.js`)

```javascript
import { useState, useEffect } from 'react';
import apiClient from '../../../core/api/b2cClient';

function WorkspaceDashboard() {
    const [workspaces, setWorkspaces] = useState([]);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        loadWorkspaces();
    }, []);
    
    const loadWorkspaces = async () => {
        try {
            const response = await apiClient.get('/api/b2c/workspaces');
            setWorkspaces(response.data);
        } catch (error) {
            console.error('Failed to load workspaces:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <h1>My Workspaces</h1>
            {workspaces.map(workspace => (
                <div key={workspace.id}>
                    <h3>{workspace.name}</h3>
                    <p>Type: {workspace.type}</p>
                    <p>Tier: {workspace.subscription_tier}</p>
                </div>
            ))}
        </div>
    );
}
```

## Subscription Tier Implementation

### Database

Add subscription limits to workspace settings:
```python
settings = {
    "limits": {
        "users": 5,      # Max team members
        "storage_gb": 10,
        "api_calls_per_month": 10000
    }
}
```

### Middleware

Create usage tracking middleware:
```python
async def check_workspace_limits(workspace_id: UUID, resource: str):
    workspace = await get_workspace(workspace_id)
    limits = workspace.settings.get("limits", {})
    usage = await get_usage(workspace_id)
    
    if usage[resource] >= limits[resource]:
        raise HTTPException(
            status_code=403,
            detail=f"Workspace limit exceeded for {resource}"
        )
```

## Testing

Test the B2C module:
```bash
# Test model imports
docker-compose exec backend python -c "from services.b2c.models import Workspace, B2CUser; print('✓ Models work')"

# Test database
docker-compose exec postgres psql -U sso_user -d sso_db -c "SELECT COUNT(*) FROM b2c.workspaces;"

# Test API (after implementing)
curl http://localhost:8000/api/b2c/workspaces
```

## Next Steps

1. Implement user registration with auto workspace creation
2. Add workspace switching in frontend header
3. Implement team invitations
4. Add subscription management (Stripe/Paddle)
5. Add usage tracking and limits
6. Implement workspace analytics

## Resources

- SQLAlchemy Models: `backend/services/b2c/models/`
- API Routers: `backend/services/b2c/routers/`
- Frontend Pages: `frontend/src/modules/b2c/pages/`
- Database Schema: Review migration `014_create_b2c_tables.sql`
