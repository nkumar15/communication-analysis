# B2B Tenant Onboarding Flow

**Audience:** Product Managers, Frontend Developers, Backend Engineers

This document provides a comprehensive view of the B2B tenant onboarding process, from platform admin invitation through tenant activation and SSO configuration.

For related security details, see:
- [Authentication Architecture](./authentication.md) - Token lifecycle & Mobile Auth
- [Multi-Tenant Isolation](./multi-tenant-isolation.md) - RLS Mechanics

---

## Overview

The B2B tenant onboarding is a multi-step process that involves:

1. **Platform Admin** creates a tenant and sends activation invitation
2. **Tenant Owner** receives email with activation link
3. **Tenant Owner** validates and activates their organization
4. **Tenant Owner** configures SSO settings (optional)
5. **Tenant** invites team members

---

## Complete Onboarding Flow

```mermaid
sequenceDiagram
    participant PA as Platform Admin
    participant API as Backend API
    participant DB as PostgreSQL
    participant Firebase as Firebase Auth
    participant Email as Email Service
    participant Owner as Tenant Owner
    participant Frontend as B2B Frontend

    Note over PA,Email: Step 1: Platform Admin Creates Tenant
    
    PA->>API: POST /api/platform/b2b/tenants/onboard
    Note right of PA: {company_name, domain, owner_email}
    
    API->>API: Verify platform_admin role
    API->>DB: Check domain uniqueness
    
    API->>Firebase: Create Firebase Tenant
    Firebase-->>API: firebase_tenant_id
    
    API->>DB: INSERT tenant (status='pending')
    Note right of DB: activation_token generated<br/>expires_at = now + 48h
    
    API->>DB: Seed default roles from templates
    API->>DB: Create "Default Team"
    API->>DB: Create owner invitation (reuses activation_token)
    
    API->>Email: Send activation email
    Note right of Email: Activation URL with token
    
    API-->>PA: 201 {tenant_id, activation_url}
    
    Note over Owner,Frontend: Step 2: Owner Receives & Validates Invitation
    
    Email->>Owner: Activation email with link
    Owner->>Frontend: Click activation link
    Frontend->>API: GET /api/public/activate/validate/{token}
    
    API->>DB: SELECT tenant WHERE activation_token = ?
    API->>API: Check token not expired
    API->>API: Check tenant status = 'pending'
    
    alt Token Valid
        API-->>Frontend: 200 {tenant_info, owner_email}
        Frontend->>Frontend: Show activation page
    else Token Invalid/Expired
        API-->>Frontend: 404/410 Error
        Frontend->>Frontend: Show error message
    end
    
    Note over Owner,Firebase: Step 3: Owner Authenticates & Activates
    
    Owner->>Frontend: Click "Activate Organization"
    Frontend->>Firebase: Login with SSO
    Note right of Frontend: Uses tenant's Firebase config
    Firebase-->>Frontend: ID Token (uid, email)
    
    Frontend->>API: POST /api/activate/complete
    Note right of Frontend: {token, id_token}
    
    API->>Firebase: Verify ID token
    Firebase-->>API: Decoded token {uid, email}
    
    API->>API: Verify email matches owner_email
    API->>DB: BEGIN TRANSACTION
    
    API->>DB: UPDATE tenant SET activation_status='active'
    API->>DB: INSERT owner user (firebase_uid, email)
    API->>DB: Assign Owner role to user
    API->>DB: Add user to Default Team
    API->>DB: Mark invitation as accepted
    
    API->>DB: COMMIT
    
    API-->>Frontend: 200 {success, tenant_id, user_id}
    Frontend->>Frontend: Redirect to B2B dashboard
    
    Note over Owner,Frontend: Step 4: Owner Configures SSO (Optional)
    
    Owner->>Frontend: Navigate to Settings > SSO
    Frontend->>API: GET /api/b2b/auth-providers
    API->>DB: SELECT auth_providers WHERE tenant_id
    API-->>Frontend: 200 {providers: []}
    
    Owner->>Frontend: Add SSO Provider
    Note right of Owner: OIDC, SAML, Google, etc.
    
    Frontend->>API: POST /api/b2b/auth-providers
    Note right of Frontend: {provider_type, config_data}
    
    API->>API: Verify owner/admin role
    API->>DB: INSERT auth_provider
    API->>Firebase: Configure OIDC/SAML provider
    Firebase-->>API: provider_id
    
    API->>DB: UPDATE auth_provider SET provider_id
    API-->>Frontend: 201 {provider}
    
    Frontend->>Frontend: Show success message
    
    Note over Owner,Frontend: Step 5: Owner Invites Team Members
    
    Owner->>Frontend: Navigate to Team > Invite
    Frontend->>API: POST /api/b2b/invitations/invite
    Note right of Frontend: {email, role, team_id}
    
    API->>API: Verify owner/admin permission
    API->>DB: INSERT invitation
    API->>Email: Send invitation email
    API-->>Frontend: 201 {invitation_id}
```

---

## Detailed Step Breakdown

### Step 1: Platform Admin Creates Tenant

**Endpoint:** `POST /api/platform/b2b/tenants/onboard`

**Request:**
```json
{
  "company_name": "Acme Corporation",
  "domain": "acme.com",
  "owner_email": "admin@acme.com"
}
```

**Backend Process:**
1. Validates platform admin role
2. Checks domain uniqueness
3. Creates Firebase tenant (multi-tenancy isolation)
4. Generates activation token (48-hour expiry)
5. Creates database records:
   - Tenant (status: `pending`)
   - Default roles from templates  
   - Default team
   - Owner invitation (reuses activation token)
6. Sends activation email to owner

**Response:**
```json
{
  "tenant_id": "uuid",
  "tenant_name": "Acme Corporation",
  "domain": "acme.com",
  "owner_email": "admin@acme.com",
  "firebase_tenant_id": "acme-xxxxx",
  "activation_url": "https://app.example.com/activate/{token}",
  "activation_token": "secret_token",
  "expires_at": "2024-01-15T12:00:00Z"
}
```

---

### Step 2: Owner Validates Activation Link

**Endpoint:** `GET /api/public/activate/validate/{token}`

**Backend Process:**
1. Looks up tenant by activation token
2. Validates:
   - Token exists
   - Not expired
   - Tenant status is `pending`
3. Returns tenant information for display

**Response:**
```json
{
  "valid": true,
  "tenant": {
    "id": "uuid",
    "name": "Acme Corporation",
    "domain": "acme.com"
  },
  "owner_email": "admin@acme.com",
  "firebase_config": {
    "tenant_id": "acme-xxxxx",
    "api_key": "...",
    "auth_domain": "..."
  },
  "expires_at": "2024-01-15T12:00:00Z"
}
```

---

### Step 3: Owner Completes Activation

**Endpoint:** `POST /api/activate/complete`

**Request:**
```json
{
  "activation_token": "secret_token",
  "id_token": "firebase_id_token"
}
```

**Backend Process:**
1. Verifies Firebase ID token
2. Validates email matches owner_email  
3. **Atomic Transaction:**
   - Updates tenant status: `pending` → `active`
   - Creates owner user record
   - Assigns Owner role
   - Adds to Default Team
   - Marks invitation as accepted
4. Commits all changes

**Response:**
```json
{
  "success": true,
  "tenant_id": "uuid",
  "user_id": "uuid",
  "message": "Organization activated successfully"
}
```

**Frontend Behavior:**
- Redirects to B2B dashboard
- Stores authentication token
- User can now access the application

---

### Step 4: SSO Configuration (Optional)

**Endpoint:** `POST /api/b2b/auth-providers`

**Request:**
```json
{
  "provider_type": "oidc",
  "provider_name": "Okta SSO",
  "config_data": {
    "client_id": "okta_client_id",
    "client_secret": "okta_secret",
    "issuer": "https://okta.example.com"
  }
}
```

**Backend Process:**
1. Verifies owner/admin role
2. Creates auth provider record in database
3. Configures provider in Firebase
4. Links Firebase provider_id to database record

**Response:**
```json
{
  "id": "uuid",
  "provider_type": "oidc",
  "provider_id": "oidc.okta",
  "provider_name": "Okta SSO",
  "status": "active"
}
```

---

### Step 5: Team Member Invitation

**Endpoint:** `POST /api/b2b/invitations/invite`

**Request:**
```json
{
  "email": "user@acme.com",
  "role": "admin",
  "team_id": "uuid"
}
```

**Process:** See [User Invitation Flow](#user-invitation-flow) below.

---

## User Invitation Flow

After tenant activation, owners and admins can invite team members.

```mermaid
sequenceDiagram
    participant Admin as Tenant Admin
    participant API as Backend API
    participant DB as Database
    participant Email as Email Service
    participant User as Invited User
    participant Firebase as Firebase Auth

    Admin->>API: POST /api/b2b/invitations/invite
    Note right of Admin: {email, role, team_id}
    
    API->>API: Verify admin/owner role
    API->>DB: Check user doesn't exist
    API->>DB: INSERT invitation
    API->>Email: Send invitation email
    API-->>Admin: 201 {invitation_id}
    
    Email->>User: Invitation email
    User->>API: GET /api/b2b/invitations/{token}
    Note right of User: Public endpoint
    
    API->>DB: SELECT invitation (RLS bypass)
    API->>API: Check not expired
    API-->>User: 200 {tenant_info, role, team}
    
    User->>Firebase: Login with tenant SSO
    Firebase-->>User: ID Token
    
    User->>API: POST /api/b2b/invitations/{token}/accept
    Note right of User: {id_token}
    
    API->>Firebase: Verify ID token
    API->>API: Check email matches invitation
    API->>DB: BEGIN TRANSACTION
    API->>DB: INSERT user
    API->>DB: Assign role
    API->>DB: Add to team
    API->>DB: Mark invitation accepted
    API->>DB: COMMIT
    
    API-->>User: 200 {success, user_id}
    User->>API: Access B2B application
```

---

## State Transitions

### Tenant States

```mermaid
stateDiagram-v2
    [*] --> Pending: Platform Admin creates tenant
    Pending --> Active: Owner completes activation
    Active --> Deactivated: Platform Admin deactivates
    Deactivated --> Active: Platform Admin reactivates
    
    note right of Pending
        - activation_token generated
        - 48-hour expiry
        - Owner invitation sent
    end note
    
    note right of Active
        - Owner user created
        - Can invite team members
        - Can configure SSO
    end note
    
    note right of Deactivated
        - All users blocked
        - API returns 403
        - Data preserved
    end note
```

### Invitation States

```mermaid
stateDiagram-v2
    [*] --> Pending: Invitation created
    Pending --> Accepted: User completes signup
    Pending --> Expired: 7 days elapsed
    Pending --> Cancelled: Admin cancels
    
    note right of Pending
        - invitation_token valid
        - Email sent
        - Awaiting acceptance
    end note
    
    note right of Accepted
        - User created
        - Role assigned
        - Team membership added
    end note
```

---

## Security Considerations

### RLS (Row Level Security)

1. **Platform Admin Context:** 
   - Required for cross-tenant operations
   - Set via `app.is_platform_admin = true`

2. **Tenant Context:**
   - Set after authentication: `app.current_tenant_id = uuid`
   - All queries automatically filtered by tenant_id

3. **Public Endpoints:**
   - Validation endpoints bypass RLS temporarily
   - Immediately scope to specific tenant after lookup

### Token Security

1. **Activation Tokens:**
   - 32-byte URL-safe random string
   - 48-hour expiration
   - Single-use (marked used on activation)

2. **Invitation Tokens:**
   - 32-byte URL-safe random string  
   - 7-day expiration
   - Single-use (marked used on acceptance)

### Email Verification

- Owner email must match Firebase authentication email
- Prevents unauthorized activations
- Enforced during `complete_activation`

---

## API Endpoints Reference

### Platform Admin Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/platform/b2b/tenants/onboard` | Create and send activation |
| POST | `/api/platform/b2b/tenants/{id}/resend` | Resend activation email |
| PATCH | `/api/platform/b2b/tenants/{id}/deactivate` | Deactivate tenant |
| PATCH | `/api/platform/b2b/tenants/{id}/reactivate` | Reactivate tenant |

### Public Endpoints (No Auth)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/public/activate/validate/{token}` | Validate activation link |
| GET | `/api/b2b/invitations/{token}` | View invitation details |

### Authenticated Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/activate/complete` | Complete activation |
| POST | `/api/b2b/invitations/invite` | Invite team member |
| POST | `/api/b2b/invitations/{token}/accept` | Accept invitation |
| POST | `/api/b2b/auth-providers` | Configure SSO |

---

## Error Handling

### Common Error Scenarios

1. **Expired Activation Token**
   - Status: 410 Gone
   - Solution: Platform admin resends activation

2. **Domain Already Exists**
   - Status: 409 Conflict
   - Solution: Use different domain or contact existing tenant

3. **Email Mismatch During Activation**
   - Status: 403 Forbidden
   - Solution: Use correct email address for SSO login

4. **Tenant Deactivated**
   - Status: 403 Forbidden
   - Message: "This organization has been deactivated"
   - Solution: Contact platform admin

---

## Best Practices

### For Platform Admins

1. **Domain Validation:** Verify company owns the domain before onboarding
2. **Email Verification:** Ensure owner_email is correct and accessible
3. **Monitoring:** Track activation rates and follow up on pending tenants
4. **Resend Capability:** Use resend activation for expired tokens

### For Tenant Owners

1. **Immediate Activation:** Complete activation within 48 hours
2. **SSO Configuration:** Set up SSO providers before inviting team
3. **Role Assignment:** Use principle of least privilege for team members
4. **Team Organization:** Create teams before sending invitations

### For Developers

1. **Atomic Transactions:** All activation steps in single transaction
2. **Idempotency:** Handle duplicate onboarding requests gracefully
3. **RLS Context:** Always set proper context before database operations
4. **Error Recovery:** Provide clear paths for error scenarios

---

## Related Documentation

- **[Authentication Architecture](./authentication.md)** - Token lifecycle and security
- **[Multi-Tenant Isolation](./multi-tenant-isolation.md)** - RLS implementation
- **[RBAC System](./rbac.md)** - Role and permission management
- **[Team Management](./teams.md)** - Team structure and membership
