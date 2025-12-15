# B2C System Architecture Brainstorm

## 1. Authentication Strategy

### Option A: Simplified Firebase Auth (NO GCIP Multi-Tenancy)
**Recommended for B2C**

Since B2C users are **individuals** (not enterprises with corporate SSO), you **do NOT need GCIP Multi-Tenancy**.

#### Setup:
- **Single Firebase Project** (not tenant-per-user)
- **Native Firebase Auth Providers**:
  - Google Sign-In (via `signInWithPopup` or native SDK)
  - Email/Password (via `createUserWithEmailAndPassword`)
  - GitHub, Apple, etc. (optional)

#### Flow:
```
1. User clicks "Sign Up with Google" or "Sign Up with Email"
2. Firebase SDK handles authentication
3. Frontend receives Firebase ID Token
4. Call POST /api/b2c/auth/sync-user with token
5. Backend verifies token, creates Workspace + User record
```

#### Why NOT GCIP for B2C?
- **GCIP is for Enterprise SSO** (Okta, Auth0, Azure AD per tenant)
- B2C users just need simple social/email login
- Native Firebase Auth is simpler, cheaper, faster

---

## 2. Workspace Model

### User → Workspace Relationship

```
┌─────────────────┐
│   B2C User      │
│ (Firebase UID)  │
└────────┬────────┘
         │
         ├─── Personal Workspace (Auto-created)
         └─── Team Workspaces (via invitation)
```

### Database Schema

```sql
-- b2c.workspaces
CREATE TABLE b2c.workspaces (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(20), -- 'personal' | 'team'
    owner_id UUID REFERENCES b2c.users(id),
    subscription_id UUID REFERENCES b2c.subscriptions(id),
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- b2c.users
CREATE TABLE b2c.users (
    id UUID PRIMARY KEY,
    firebase_uid VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    personal_workspace_id UUID REFERENCES b2c.workspaces(id),
    created_at TIMESTAMP
);

-- b2c.workspace_members (for team workspaces)
CREATE TABLE b2c.workspace_members (
    workspace_id UUID REFERENCES b2c.workspaces(id),
    user_id UUID REFERENCES b2c.users(id),
    role VARCHAR(50), -- 'owner' | 'admin' | 'member'
    joined_at TIMESTAMP,
    PRIMARY KEY (workspace_id, user_id)
);
```

### Signup Flow

```
1. User signs up via Google/Email
2. Backend creates:
   - User record (with firebase_uid)
   - Personal Workspace (auto-created, type='personal')
   - Links: user.personal_workspace_id → workspace.id
3. User lands in their personal workspace dashboard
```

---

## 3. Data Isolation Strategy

### Workspace-Scoped RLS (Row Level Security)

Unlike B2B (tenant-scoped), B2C uses **workspace-scoped** isolation.

#### RLS Policy Example:
```sql
-- Only see data in workspaces you're a member of
CREATE POLICY workspace_data_access ON b2c.projects
USING (
    workspace_id IN (
        SELECT workspace_id FROM b2c.workspace_members
        WHERE user_id = current_setting('app.current_user_id')::uuid
    )
);
```

#### Context Setting:
```python
# Instead of set_tenant_context (B2B)
await rls_service.set_user_context(db, user_id=current_user['id'])
```

#### Middleware:
```python
@router.get("/api/b2c/projects")
async def list_projects(
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    # Set RLS context to current user
    await rls_service.set_user_context(db, current_user['id'])
    
    # Query automatically filtered by RLS
    result = await db.execute(select(Project))
    return result.scalars().all()
```

---

## 4. Billing & Subscriptions

### Stripe Integration Model

```sql
-- b2c.subscriptions
CREATE TABLE b2c.subscriptions (
    id UUID PRIMARY KEY,
    workspace_id UUID REFERENCES b2c.workspaces(id),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    plan_tier VARCHAR(50), -- 'free' | 'premium' | 'ultimate'
    status VARCHAR(50), -- 'active' | 'canceled' | 'past_due'
    current_period_end TIMESTAMP,
    created_at TIMESTAMP
);
```

### Plans & Limits

| Plan | Price | Limits |
|------|-------|--------|
| **Free** | $0/mo | 5 projects, 1 personal workspace |
| **Premium** | $12/mo | Unlimited projects, team workspaces (up to 5 members) |
| **Ultimate** | $49/mo | Unlimited everything, SSO (optional) |

### Subscription Flow

```
1. User creates account → FREE tier (personal workspace)
2. User wants team workspace → Upgrade to PRO
3. User clicks "Upgrade" → redirected to Stripe Checkout
4. Stripe webhook → update subscription status
5. Backend enables team workspace creation
```

### Quota Enforcement

```python
async def create_project(workspace_id: UUID, db: AsyncSession):
    workspace = await db.get(Workspace, workspace_id)
    subscription = await db.get(Subscription, workspace.subscription_id)
    
    # Check quota
    if subscription.plan_tier == 'free':
        project_count = await db.scalar(
            select(func.count(Project.id)).where(Project.workspace_id == workspace_id)
        )
        if project_count >= 5:
            raise HTTPException(403, "Upgrade to Premium for unlimited projects")
    
    # Create project...
```

---

## 5. Key Differences: B2B vs B2C

| Aspect | B2B | B2C |
|--------|-----|-----|
| **Auth** | GCIP Multi-Tenancy + OIDC | Native Firebase Auth (Google, Email) |
| **Isolation Unit** | Tenant (Company) | Workspace (User or Team) |
| **RLS Context** | `app.current_tenant_id` | `app.current_user_id` |
| **Billing** | Enterprise contracts, Tenant-level | Stripe subscriptions, Workspace-level |
| **User Onboarding** | Platform Admin invites Tenant Owner | Self-signup, instant activation |

---

## 6. Recommended Architecture

### Phase 1: Personal Workspaces Only
1. Native Firebase Auth (Google + Email/Password)
2. Auto-create personal workspace on signup
3. Free tier only (no billing yet)
4. Workspace-scoped RLS

### Phase 2: Team Workspaces
1. Add `workspace_members` table
2. Invite flow (similar to B2B invitations)
3. Role-based access within workspace

### Phase 3: Billing
1. Stripe integration
2. Subscription model (Free/Premium/Ultimate)
3. Quota enforcement middleware
4. Stripe webhooks for status updates

---

## 7. Firebase Setup Recommendation

**Do NOT use GCIP Multi-Tenancy for B2C.**

### What you need:
1. **Single Firebase Project** (e.g., `my-saas-app-b2c`)
2. **Enable Auth Providers**:
   - Google (via OAuth 2.0)
   - Email/Password
3. **Frontend SDK**:
   ```javascript
   import { getAuth, signInWithPopup, GoogleAuthProvider } from 'firebase/auth';
   
   const auth = getAuth();
   const provider = new GoogleAuthProvider();
   signInWithPopup(auth, provider);
   ```

### Cost Comparison:
- **GCIP**: $0.015/MAU (Monthly Active User) + multi-tenant overhead
- **Native Firebase Auth**: FREE up to 50,000 MAUs, then $0.0055/MAU

For B2C with potentially high user volume, **native Firebase Auth is significantly cheaper**.

---

## Next Steps

1. **Confirm approach**: Personal-only first, or go straight to Team Workspaces?
2. **Billing timing**: Implement subscriptions in Phase 1, or defer?
3. **Create specs**:
   - `authentication.md` (Firebase native auth flow)
   - `workspaces.md` (Personal + Team workspace model)
   - `subscriptions.md` (Stripe integration)
