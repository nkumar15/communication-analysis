# Functional Specification: Tenant Onboarding

**ID**: `SPEC-01`
**Requirements**: `ONB-01`, `ONB-02`, `ONB-03`
**Feature**: Automated Tenant Provisioning & Activation
**Status**: Live

## 1. Overview
Tenant onboarding is an **Invitation-Based** process. It is **NOT** self-service. A rigorous vetting process is assumed before a Platform Admin triggers this flow.

## 2. User Stories

### ONB-01: Platform Admin Invite
**As a** SaaS Platform Admin (Super Admin),
**I want to** invite a new Tenant Owner by email,
**So that** I can onboard vetted customers onto the platform.

**Acceptance Criteria:**
1.  Admin accesses `POST /api/platform/tenants` (or CLI).
2.  Admin provides: `company_name`, `subdomain`, `owner_email`.
3.  System checks for domain/email uniqueness.
4.  System creates `Tenant` record with status `PENDING`.
5.  System generates a secure, time-limited Activation Token (48 hours).
6.  System sends an email to `owner_email` with the activation link.

### ONB-02: Activation Email
**As a** System,
**I want to** send a branded activation email,
**So that** the user trusts the source and clicks the link.

**Acceptance Criteria:**
1.  Email subject: "Activate your [Platform Name] Account".
2.  Email contains a **Universal Link** (supporting Deep Linking):
    -   Web: `https://app.domain.com/activate?token=xyz`
    -   Mobile: Opens App directly if installed.
3.  Link expires in 48 hours.

### ONB-03: Tenant Owner Activation
**As a** Tenant Owner (Invited User),
**I want to** click the link and set up my account,
**So that** I can access my dashboard.

**Acceptance Criteria:**
1.  User clicks link -> Redirects to frontend `/activate` page.
2.  Frontend validates token via API `GET /api/activate/validate/{token}`.
    -   *If invalid/expired*: Show error message.
    -   *If valid*: Show "Welcome [Company Name]" screen.
3.  User clicks "Activate & Login".
4.  User performs SSO Login (OIDC) to verify identity.
5.  System updates `Tenant` status to `ACTIVE`.
6.  System creates the user as `Admin` in the new tenant.
7.  User is redirected to the Tenant Dashboard.

## 4. User Interface Requirements

**Design Compliance**: All UI must strictly follow [`SPEC-DESIGN-01`](./ui-design.md).

### 4.1. Supported Platforms
This feature must be implemented for both:
- **Web**: Admin Dashboard (Desktop Optimized)
- **Mobile**: Tenant App (iOS/Android)

### 4.2. Activation Flow (Web)
**Wireframe Reference**: `WF-ONB-Web` (TBD)
**Components**:
- `AdminLayout`: Standard wrapper.
- `ActivationCard`: Centered card on public page.
- `StatusBadge`: To show 'Pending' state.

### 4.3. Activation Flow (Mobile)
**Wireframe Reference**: `WF-ONB-Mobile` (TBD)
**Components**:
- `SafeAreaView`: React Native wrapper.
- `DeepLinkHandler`: To catch `app.domain.com/activate`.
- Native-styled Inputs and Actions.

## 5. Technical Implementation
*   **API**: `b2b-api`, `platform-api`
*   **Database**: `tenants` (status), `users` (admin)
*   **Modules**: `TenantService`, `InvitationService`, `EmailService`

