# SPEC-07: Mobile App Support

**Status**: Active / Implemented
**Platform**: iOS & Android (React Native)
**Last Updated**: 2025-12-11

## Overview

The Enterprise SSO mobile app allows users to access their tenant workspace on the go. It shares the same backend API as the web platform but utilizes native-specific authentication flows to ensure a secure and seamless user experience.

## 1. Authentication Strategy

Mobile authentication differs from web to support native usability guidelines (avoiding embedded webviews for login).

### 1.1 Native Login (No Webviews)
*   **Technology**: `react-native-app-auth` (AppAuth-iOS / AppAuth-Android).
*   **Flow**:
    1.  User enters email.
    2.  `POST /api/b2b/auth/resolve-tenant`: Returns `mobile_provider_id` (OIDC) and config.
    3.  `GET /api/b2b/auth/oidc-config/{provider_id}`: Returns dynamic `issuer` and `client_id` for that tenant.
    4.  App opens System Browser (SFSafariViewController / Chrome Custom Tabs) for IDP login.
    5.  User authenticates with their corporate credentials (e.g., Okta).
    6.  IDP redirects back to App via Deep Link (e.g., `com.company.sso://callback`).

### 1.2 Token Exchange
Since the AppAuth flow returns an IDP Token (not a Firebase Token), we perform a server-side exchange:
*   **Endpoint**: `POST /api/b2b/auth/mobile-login`
*   **Input**: `oidc_id_token`, `provider_id`.
*   **Process**: Backend verifies with GCIP -> Mints **Firebase Custom Token**.
*   **Output**: Firebase Custom Token.
*   **Final Step**: App calls `auth().signInWithCustomToken(token)`.

## 2. Cross-Platform Consistency

### 2.1 Identity Reconciliation
Mobile and Web logins may result in different `firebase_uid` values due to the difference between GCIP Federation (Web) and Custom Token Minting (Mobile).
*   **Solution**: The backend `UserService` treats **Email** as the canonical identity.
*   **Behavior**:
    *   If a Web User logs in on Mobile, the API looks up by Email.
    *   The User ID (UUID) remains the same.
    *   The `firebase_uid` in the database is *not* overwritten if it differs, preserving the stable Web identity while allowing Mobile access.

## 3. Feature Parity & Limitations

The following matrix evaluates all web features for mobile inclusion. Features are categorized by functionality area with clear rationale for inclusion decisions.

### Legend
- ✅ **Include**: Full feature implementation in mobile
- 🟡 **Partial**: Limited/simplified version for mobile
- ❌ **Exclude**: Not suitable for mobile (web-only)
- 🔮 **Future**: Planned for later mobile versions

---

## B2B Features Decision Matrix

### Authentication & Identity

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| SSO Login (OIDC) | ✅ | ✅ | **P0** | Core functionality via Native AppAuth |
| Email/Password Login | ✅ | ✅ | **P0** | Fallback auth method |
| Multi-Factor Authentication | ✅ | ✅ | **P1** | Security critical, native 2FA support |
| Tenant Resolution | ✅ | ✅ | **P0** | Required for multi-tenant access |
| Tenant Switching | ✅ | 🟡 | **P1** | Requires re-login; streamline in v2 |
| Password Reset | ✅ | ✅ | **P0** | Self-service via deep link |
| Session Management | ✅ | ✅ | **P0** | Token refresh, biometric unlock |

### Dashboard & Analytics

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| Owner Dashboard | ✅ | 🟡 | **P1** | Show key metrics only (users, teams, health) |
| Admin Dashboard | ✅ | 🟡 | **P1** | User stats, pending actions, quick access |
| Member Dashboard | ✅ | ✅ | **P0** | My teams, tasks, personal activity |
| Viewer Dashboard | ✅ | ✅ | **P1** | Read-only overview |
| Org Health Score | ✅ | ❌ | **P3** | Complex visualization, desktop-suited |
| Audit Log Preview | ✅ | 🟡 | **P2** | Recent events only, full view on web |
| Customizable Widgets | ✅ | ❌ | **P3** | Limited screen space |

### User Management

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Users List | ✅ | ✅ | **P1** | Essential for admins on-the-go |
| Invite Single User | ✅ | ✅ | **P1** | Common admin task |
| Bulk User Invitations (CSV) | ✅ | ❌ | **P3** | Complex file upload, desktop workflow |
| Edit User Roles | ✅ | 🟡 | **P2** | Simple role picker, no bulk edit |
| Deactivate/Remove User | ✅ | 🟡 | **P2** | Single user only, no bulk actions |
| View User Profile | ✅ | ✅ | **P1** | View details, last login, teams |
| Resend Invitation | ✅ | ✅ | **P2** | Quick action for pending invites |
| Accept Invitation | ✅ | ✅ | **P0** | Via deep link from email |

### Role-Based Access Control (RBAC)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Roles | ✅ | ✅ | **P1** | Display available roles |
| View Permissions | ✅ | 🟡 | **P2** | Read-only list, no editing |
| Create Custom Roles | ✅ | ❌ | **P3** | Complex configuration, desktop task |
| Edit Role Permissions | ✅ | ❌ | **P3** | Granular matrix editing unsuitable for mobile |
| Assign Roles to Users | ✅ | ✅ | **P1** | Via user profile screen |
| Team Role Management | ✅ | 🟡 | **P2** | Simple team role assignment |

### Team Management

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Teams List | ✅ | ✅ | **P0** | Core navigation element |
| View Team Details | ✅ | ✅ | **P0** | Members, projects, stats |
| Create Team | ✅ | ✅ | **P1** | Simple form suitable for mobile |
| Edit Team Settings | ✅ | 🟡 | **P2** | Name/description only, no advanced settings |
| Delete Team | ✅ | 🟡 | **P2** | Confirmation dialog required |
| Add Team Members | ✅ | ✅ | **P1** | Search and select from org users |
| Remove Team Members | ✅ | ✅ | **P1** | Simple swipe-to-remove action |
| Assign Team Roles | ✅ | ✅ | **P1** | Manager/Contributor/Reader picker |
| Leave Team | ✅ | ✅ | **P1** | Self-service exit |

### Projects & Tasks

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Projects List | ✅ | ✅ | **P0** | Core productivity feature |
| View Project Details | ✅ | ✅ | **P0** | Tasks, members, progress |
| Create Project | ✅ | ✅ | **P0** | Quick project creation |
| Edit Project | ✅ | ✅ | **P1** | Name, description, team assignment |
| Delete Project | ✅ | 🟡 | **P2** | With confirmation |
| View Tasks List | ✅ | ✅ | **P0** | Filter by status, assignee, priority |
| Create Task | ✅ | ✅ | **P0** | Essential mobile task |
| Edit Task | ✅ | ✅ | **P0** | Title, description, status, assignee |
| Update Task Status | ✅ | ✅ | **P0** | Swipe gestures for status change |
| Assign Task | ✅ | ✅ | **P0** | Quick assignment picker |
| Task Comments | ✅ | ✅ | **P0** | Threaded discussions |
| File Attachments | ✅ | 🟡 | **P1** | View only, upload via camera/gallery |
| Bulk Task Actions | ✅ | ❌ | **P3** | Desktop-suited multi-select |

### Billing & Subscriptions (B2B)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Subscription Status | ✅ | 🟡 | **P2** | Read-only current plan info |
| Upgrade/Downgrade Plan | ✅ | ❌ | **P3** | Redirect to web for checkout |
| Payment Method Management | ✅ | ❌ | **P3** | Complex Stripe integration, use web |
| View Invoices | ✅ | 🟡 | **P2** | List with PDF download links |
| Download Invoice PDF | ✅ | ✅ | **P2** | Open in native PDF viewer |
| Cancel Subscription | ✅ | ❌ | **P3** | Critical action, requires web confirmation |
| Apply Coupon Code | ✅ | ❌ | **P3** | Part of checkout flow (web) |
| Seat Management | ✅ | ❌ | **P3** | View-only on mobile, management on web |

### Platform Admin (B2B)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| Tenant Onboarding | ✅ | ❌ | **N/A** | Complex multi-step process, desktop only |
| Tenant Management | ✅ | 🟡 | **P3** | View tenant list, basic stats only |
| Tenant Impersonation | ✅ | ❌ | **N/A** | Security-sensitive, desktop only |
| Platform Dashboard | ✅ | 🟡 | **P3** | High-level stats only |
| System Audit Logs | ✅ | ❌ | **N/A** | Complex filtering, desktop only |
| Manual Billing Actions | ✅ | ❌ | **N/A** | Refunds, invoices - desktop only |

### Settings & Preferences

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| Profile Settings | ✅ | ✅ | **P1** | Name, email, avatar update |
| Notification Preferences | ✅ | ✅ | **P0** | Push notification config critical |
| App Theme (Dark/Light) | ✅ | ✅ | **P1** | Native theme support |
| Language Preferences | ✅ | ✅ | **P2** | If i18n implemented |
| Tenant Settings | ✅ | 🟡 | **P2** | View-only, basic info |
| Security Settings | ✅ | 🟡 | **P2** | View sessions, no complex config |
| Auth Provider Config | ✅ | ❌ | **N/A** | OIDC/SAML setup - desktop only |

---

## B2C Features Decision Matrix

### Authentication & Identity (B2C)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| Social Login (Google) | ✅ | ✅ | **P0** | Native iOS/Android social auth |
| Social Login (GitHub) | ✅ | ✅ | **P1** | Standard OAuth flow |
| Social Login (Apple) | ✅ | ✅ | **P0** | Required for App Store |
| Email/Password Signup | ✅ | ✅ | **P0** | Standard auth method |
| Email Verification | ✅ | ✅ | **P0** | Via deep link |
| Password Reset | ✅ | ✅ | **P0** | Self-service flow |
| Profile Management | ✅ | ✅ | **P1** | Display name, avatar |

### Workspace Management (B2C)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Personal Workspace | ✅ | ✅ | **P0** | Core container for user data |
| View Team Workspaces | ✅ | ✅ | **P0** | List all accessible workspaces |
| Create Team Workspace | ✅ | ✅ | **P1** | Premium feature, simple creation |
| Switch Workspace | ✅ | ✅ | **P0** | Critical navigation |
| Edit Workspace Settings | ✅ | 🟡 | **P2** | Name/description only |
| Delete Workspace | ✅ | ❌ | **P3** | Critical action, desktop confirmation |
| Invite to Workspace | ✅ | ✅ | **P1** | Email-based invitations |
| Accept Workspace Invite | ✅ | ✅ | **P0** | Via deep link |
| Remove Workspace Members | ✅ | 🟡 | **P2** | Single member removal only |
| Leave Workspace | ✅ | ✅ | **P1** | Self-service |
| Transfer Ownership | ✅ | ❌ | **P3** | Critical action, desktop only |

### Subscriptions & Billing (B2C)

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Subscription Status | ✅ | 🟡 | **P2** | Current plan, expiry, usage |
| Upgrade Plan | ✅ | ❌ | **P3** | Redirect to web for payment |
| Cancel Subscription | ✅ | ❌ | **P3** | Critical action, web flow |
| Payment Method Management | ✅ | ❌ | **P3** | Use provider SDK on web |
| View Invoices | ✅ | 🟡 | **P2** | List with PDF links |
| Usage/Quota Tracking | ✅ | ✅ | **P1** | Show current usage vs limits |
| Subscription Renewal Alerts | ✅ | ✅ | **P1** | Push notifications |

### Content & Collaboration

| Feature | Web | Mobile | Priority | Rationale |
|---------|-----|--------|----------|-----------|
| View Projects | ✅ | ✅ | **P0** | Core feature |
| Create Projects | ✅ | ✅ | **P0** | Quick creation |
| Edit Projects | ✅ | ✅ | **P0** | Full CRUD |
| View Tasks | ✅ | ✅ | **P0** | List, filter, search |
| Create Tasks | ✅ | ✅ | **P0** | Mobile-optimized form |
| Edit Tasks | ✅ | ✅ | **P0** | Update status, assign |
| Comments | ✅ | ✅ | **P0** | Real-time discussions |
| Notifications | ✅ | ✅ | **P0** | Push for task updates |

---

## Implementation Priorities

### Phase 1 (MVP) - P0 Features
**Target**: Core mobile experience for existing users

**B2B:**
- SSO Authentication (AppAuth)
- Member Dashboard (my teams, tasks)
- View Teams & Projects
- Task CRUD operations
- Comments
- Push Notifications

**B2C:**
- Social Login (Google, Apple)
- Workspace Switching
- Projects & Tasks
- Basic Profile Management

### Phase 2 (Enhanced) - P1 Features
**Target**: Admin capabilities on mobile

**B2B:**
- User Management (view, invite, role assignment)
- Team Management (create, add/remove members)
- Advanced Dashboard views
- File attachments (view/upload)

**B2C:**
- Team Workspace creation
- Workspace invitations
- Usage tracking
- Enhanced profile settings

### Phase 3 (Advanced) - P2 Features
**Target**: Power user features

**B2B:**
- Role & Permission viewing
- Team settings
- Invoice viewing
- Audit log preview (recent only)

**B2C:**
- Workspace member management
- Subscription status viewing
- Invoice access

### Future Considerations - P3 Features
**Web-Only (Not planned for mobile):**
- Bulk operations (CSV imports, multi-select actions)
- Complex billing workflows (payment methods, plan changes)
- Platform admin functions (tenant onboarding, impersonation)
- Custom role creation and permission matrix editing
- OIDC/SAML provider configuration
- Advanced analytics and reporting

---

## Mobile-Specific Enhancements

### Features Beyond Web Parity

| Feature | Priority | Rationale |
|---------|----------|-----------|
| **Biometric Authentication** | **P1** | Face ID / Touch ID for quick re-auth |
| **Offline Mode** | **P2** | View cached tasks/projects offline |
| **Push Notifications** | **P0** | Task assignments, mentions, deadlines |
| **Camera Integration** | **P1** | Upload photos directly to tasks |
| **Location Services** | **P3** | Check-ins, location-based tasks (future) |
| **Voice Input** | **P2** | Voice-to-text for task/comment creation |
| **Home Screen Widgets** | **P2** | Quick stats, pending tasks |
| **Siri/Google Assistant Shortcuts** | **P3** | "Create task in Project X" |

---

## Technical Constraints

### Screen Size Limitations
- **Complex Tables**: User lists, audit logs → mobile uses cards/lists instead
- **Multi-column Layouts**: Admin dashboards → stacked mobile layout
- **Drag-and-drop**: Widget customization → not suitable for mobile

### Performance Considerations
- **Large Dataset Rendering**: Limited pagination and lazy loading required
- **File Uploads**: CSV bulk imports → desktop workflow
- **Real-time Sync**: Optimize for mobile networks (3G/4G)

### Security Restrictions
- **Critical Actions**: Subscription cancellation, tenant deletion → require web confirmation
- **Payment Processing**: PCI compliance → use web checkout via deep link
- **Admin Functions**: Platform impersonation → security risk, desktop only

---

## User Experience Guidelines

### Mobile-First Features
✅ **DO Include:**
- Quick actions (create task, invite user)
- Push notifications
- Swipe gestures (mark done, delete)
- Native camera/photo integration
- Offline viewing
- Biometric auth

❌ **DO NOT Include:**
- Complex multi-step wizards
- Bulk CSV operations
- Detailed analytics dashboards
- Payment form entry (use provider SDK)
- Multi-select bulk actions
- Complex permission matrix editing

## 4. Deep Linking

The mobile app supports Universal Links (iOS) and App Links (Android) for seamless workflow handling.

*   `https://app.enterprisesso.com/invite/{token}` -> Opens App -> `InviteAcceptScreen`
*   `https://app.enterprisesso.com/reset-password` -> Opens App -> `ResetPasswordScreen`
