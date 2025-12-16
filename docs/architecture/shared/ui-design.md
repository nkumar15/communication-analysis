# UI Design & Components Specification

**ID**: `SPEC-DESIGN-01`  
**Status**: Active  
**Scope**: B2B Web, B2C Web, Platform Admin, Mobile App  
**Last Updated**: 2025-12-16

---

## 1. Overview

This specification defines the **visual language**, **design tokens**, and **reusable components** for the entire SaaS platform across all three systems:

- **B2B (Multi-tenant SaaS)** - Customer-facing tenant admin portals
- **B2C (End-user App)** - Individual user workspaces and collaboration
- **Platform (Super Admin)** - Platform administration and tenant management

All implementations (Web & Mobile) must strictly adhere to these values to ensure brand consistency.

---

## 2. Design Tokens

Tokens are abstract values that represent design decisions. They must be implemented as constants in code (e.g., JS constants, Swift structs, XML resources), **not** just CSS variables.

### 2.1. Color Palette

#### Primary Actions
- `Primary Blue`: `#4F46E5` - Main actions, Links (All platforms)
- `Secondary Purple`: `#8B5CF6` - Platform Admin specific actions
- `Indigo`: `#6366F1` - Accent color for B2C

#### Feedback / State
- `Success Green`: `#10B981` - Success messages, valid states
- `Warning Orange`: `#F59E0B` - Warnings, pending actions
- `Error Red`: `#EF4444` - Destructive actions, validation errors
- `Info Blue`: `#3B82F6` - Informational messages

#### Neutrals (Shared)
- `Text Primary`: `#111827` - Main content
- `Text Secondary`: `#6B7280` - Subtitles, placeholders
- `Text Muted`: `#9CA3AF` - Disabled, inactive text
- `Border`: `#E5E7EB` - Dividers, input borders
- `Border Light`: `#F3F4F6` - Subtle dividers
- `Background`: `#F9FAFB` - Page background
- `Surface`: `#FFFFFF` - Card/Modal background
- `Dark Surface`: `#1F2937` - Sidebar, dark mode surfaces

### 2.2. Domain-Specific Colors

#### B2B Role Badges
- `Role Owner`: `#7C3AED` (Purple)
- `Role Admin`: `#DC2626` (Red)
- `Role Manager`: `#D97706` (Orange)
- `Role Member`: `#2563EB` (Blue)
- `Role Viewer`: `#6B7280` (Gray)

#### B2B Team Role Badges
- `Team Manager`: `#059669` (Green)
- `Team Contributor`: `#3B82F6` (Blue)
- `Team Reader`: `#6B7280` (Gray)

#### Status Indicators (All Platforms)
- `Status Active`: `#059669` (Green)
- `Status Inactive`: `#6B7280` (Gray)
- `Status Pending`: `#D97706` (Orange)
- `Status Expired`: `#DC2626` (Red)
- `Status Suspended`: `#EF4444` (Red)

#### Subscription Tiers (B2B)
- `Tier Free`: `#6B7280` (Gray)
- `Tier Starter`: `#3B82F6` (Blue)
- `Tier Professional`: `#8B5CF6` (Purple)
- `Tier Enterprise`: `#D97706` (Gold)

---

## 3. Typography

**Constraint**: Use system fonts where possible for performance, but fallback to Inter.

### 3.1. Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 
             'Helvetica Neue', 'Inter', sans-serif;
```

### 3.2. Scale (Web / Mobile)

| Token | Web Size (px) | Mobile Size (pt) | Weight | Usage |
|-------|---------------|------------------|--------|-------|
| `Heading 1` | 30px | 28pt | Bold (700) | Page Titles |
| `Heading 2` | 24px | 22pt | Semibold (600) | Section Headers |
| `Heading 3` | 20px | 18pt | Medium (500) | Card Titles |
| `Body Large` | 16px | 16pt | Regular (400) | Primary Text |
| `Body` | 14px | 14pt | Regular (400) | Secondary Text |
| `Caption` | 12px | 12pt | Regular (400) | Labels, Badges |
| `Small` | 11px | 11pt | Regular (400) | Footnotes |

---

## 4. Layout Guidelines

**Constraint**: Strict separation of layouts for distinct platforms.

### 4.1. B2B Web Layout (Tenant Admin)
- **Grid**: 12-column fluid grid
- **Sidebar**: Fixed width `250px` (collapsed: `80px`)
- **Header**: Fixed height `64px`
- **Content Padding**: `32px` (2rem)
- **Max Content Width**: `1400px`
- **Sidebar Color**: `#1F2937` (Dark Gray)

### 4.2. Platform Admin Web Layout (Super Admin)
- **Grid**: 12-column fluid grid
- **Sidebar**: Fixed width `260px`
- **Header**: Fixed height `72px`
- **Content Padding**: `40px` (2.5rem)
- **Max Content Width**: `1600px`
- **Sidebar Color**: `#8B5CF6` (Purple) - Distinct from B2B

### 4.3. B2C Web Layout (User Dashboard)
- **Grid**: Flexible content-based
- **Navigation**: Top navbar (no sidebar)
- **Header**: Fixed height `64px`
- **Content Padding**: `24px` (1.5rem)
- **Max Content Width**: `1200px`

### 4.4. Mobile Layout (App Flow)
- **Grid**: Single column fluid
- **Navigation**: Bottom Tab Bar or Stack Navigation
- **Touch Targets**: Minimum `44x44` points
- **Safe Area**: Must respect notch/home indicator areas
- **Content Padding**: `16px`

---

## 5. Spacing System

Use these unitless multipliers. **Base unit = 4px**.

| Token | Size | Usage |
|-------|------|-------|
| `Space-1` | 4px | Tight spacing (icon gaps) |
| `Space-2` | 8px | Small gaps (badges, chip spacing) |
| `Space-3` | 12px | Medium gaps (button padding) |
| `Space-4` | 16px | Standard gaps (card padding) |
| `Space-6` | 24px | Large gaps (section spacing) |
| `Space-8` | 32px | XL gaps (page padding) |
| `Space-12` | 48px | XXL gaps (major sections) |

---

## 6. B2B Web Components

**Location Base**: `frontend/src/modules/b2b/web/`

### 6.1. Layout Components

#### AdminLayout
**Path**: `layouts/AdminLayout.js`  
Main layout wrapper for all B2B tenant admin pages.
- **Props**: `title`, `subtitle`, `children`
- **Features**: Sidebar, Header, User Profile Dropdown, HelpWidget
- **Usage**: Wrap all B2B admin pages

#### Sidebar
**Path**: `layouts/Sidebar.js`  
Fixed left navigation sidebar with collapsible feature.
- **Features**: 
  - Collapsible (250px ↔ 80px)
  - State persisted in localStorage
  - Permission-based menu items
  - Active route highlighting
- **Menu Items**: Dashboard, Projects, Teams, Users, Roles

#### Header
**Path**: `layouts/Header.js`  
Top header bar with page title and user actions.
- **Features**: Title/subtitle display, breadcrumbs support

#### UserProfileDropdown
**Path**: `layouts/UserProfileDropdown.js`  
User profile dropdown menu.
- **Menu Items**: 
  - Account Settings
  - Audit Logs
  - Billing (Subscription, Invoices)
  - Logout

#### HelpWidget
**Path**: `../../core/components/HelpWidget.js`  
Floating bottom-right help widget with chat interface.
- **Features**:
  - Expandable chat window
  - Quick action buttons (Documentation, Tutorials, Support)
  - Message input (placeholder for chatbot)
- **Position**: Fixed bottom-right

### 6.2. Page Components

#### DashboardPage
**Path**: `pages/DashboardPage.js`  
B2B tenant dashboard with stats and widgets.
- **Widgets**: StatCards, MyTeamsWidget, MyTasksWidget, QuickActionsWidget
- **Skeleton**: `DashboardSkeleton`

#### TeamsPage
**Path**: `pages/TeamsPage.js`  
Team management and listing.
- **Features**: Create team modal, team stats, member count
- **Skeleton**: `DashboardSkeleton`

#### TeamDetailsPage
**Path**: `pages/TeamDetailsPage.js`  
Individual team details and member management.
- **Features**: Add/remove members, role assignment, team editing
- **Skeleton**: `DashboardSkeleton`

#### InvitationsPage
**Path**: `pages/InvitationsPage.js`  
User invitation and management.
- **Features**: Invite user, bulk invite, invitation stats, status tabs
- **Skeleton**: `InvitationsPageSkeleton`

#### RoleManagementPage
**Path**: `pages/RoleManagementPage.js`  
Tenant-level role and permission management.
- **Features**: Create custom roles, permission matrix, role templates
- **Skeleton**: `TableSkeleton`

#### TeamRoleManagementPage
**Path**: `pages/TeamRoleManagementPage.js`  
Team-level role management with capabilities.
- **Features**: Custom team roles, capability flags, default role setting
- **Skeleton**: `DashboardSkeleton`

#### AccountSettingsPage
**Path**: `pages/AccountSettingsPage.js`  
Tenant account settings (name, domain, logo).
- **Skeleton**: `CardSkeleton`

#### AuditLogsPage
**Path**: `pages/AuditLogsPage.js`  
Security audit log viewer with filters and export.
- **Features**: Event filtering, date range, CSV export, pagination
- **Skeleton**: `TableSkeleton`

#### SubscriptionSettingsPage
**Path**: `../../billing/SubscriptionSettingsPage.js`  
Subscription management and plan changes.
- **Features**: Current plan display, payment method, upgrade/downgrade
- **Skeleton**: `CardSkeleton`

#### InvoicesListPage
**Path**: `../../billing/InvoicesListPage.js`  
Invoice history and downloads.
- **Features**: Invoice listing, status filter, PDF download
- **Skeleton**: `TableSkeleton`

### 6.3. Utility Components

#### StatCard
**Path**: `../../core/components/StatCard.js`  
Statistics card for displaying metrics.
- **Props**: `icon`, `label`, `value`, `color`, `trend` (optional)
- **Variants**: Default, compact

#### RoleBadge
**Path**: `components/RoleBadge.js`  
Color-coded badge for B2B tenant roles.
- **Roles**: Owner (Purple), Admin (Red), Manager (Orange), Member (Blue), Viewer (Gray)
- **Style**: Pill-shaped with icon

#### TeamRoleBadge
**Path**: `components/TeamRoleBadge.js`  
Color-coded badge for team roles.
- **Roles**: Manager (Green), Contributor (Blue), Reader (Gray)

#### StatusBadge
**Path**: `../../core/components/StatusBadge.js`  
Status indicator badge.
- **Variants**: Active, Inactive, Pending, Expired, Suspended
- **Auto-color**: Based on status value

#### TabNav
**Path**: `components/TabNav.js`  
Tab navigation component with counts.
- **Props**: `tabs` (id, label, count), `activeTab`, `onTabChange`
- **Usage**: InvitationsPage status tabs

#### LoadingSkeleton
**Path**: `../../core/components/LoadingSkeleton.js`  
Collection of loading skeleton components:
- `StatCardSkeleton` - For metric cards
- `TableSkeleton` - For data tables (customizable rows)
- `CardSkeleton` - For content cards
- `DashboardSkeleton` - Composite for dashboard
- `InvitationsPageSkeleton` - Composite for invitations page

#### QuickActionsWidget
**Path**: `components/widgets/QuickActionsWidget.js`  
Quick action buttons on dashboard.
- **Actions**: Invite User, Create Team, View Billing, Manage Roles

#### MyTeamsWidget
**Path**: `components/widgets/MyTeamsWidget.js`  
User's teams display on dashboard.

#### MyTasksWidget
**Path**: `components/widgets/MyTasksWidget.js`  
User's tasks display on dashboard.

---

## 7. Platform Admin Components

**Location Base**: `frontend/src/modules/platform/web/`

### 7.1. Layout Components

#### SuperAdminLayout
**Path**: `layouts/SuperAdminLayout.js`  
Main layout wrapper for platform admin pages.
- **Features**: Distinct purple-themed sidebar, platform header
- **Styling**: Purple accent (`#8B5CF6`) to differentiate from B2B

### 7.2. Page Components

#### DashboardPage (Platform)
**Path**: `pages/DashboardPage.js`  
Platform overview with system-wide metrics.
- **Metrics**: Total tenants, active users, system health, revenue

#### TenantListPage
**Path**: `pages/TenantListPage.js`  
Tenant management and onboarding.
- **Features**: 
  - Tenant list with pagination
  - Search and filters
  - Create tenant modal
  - Tenant status management

#### TenantDetailsPage
**Path**: `pages/TenantDetailsPage.js`  
Individual tenant details and configuration.
- **Features**: 
  - Tenant info editing
  - OIDC configuration
  - Subscription view
  - Deactivate/activate tenant
  - Resend activation email

#### WorkspacesPage (B2C Management)
**Path**: `pages/WorkspacesPage.js`  
Platform view of B2C workspaces.
- **Features**: Workspace listing, stats

#### AnalyticsPage
**Path**: `pages/AnalyticsPage.js`  
Platform analytics and reporting.

#### SettingsPage (Platform)
**Path**: `pages/SettingsPage.js`  
Platform-wide settings.

### 7.3. Utility Components

#### CreateTenantModal
**Path**: `components/CreateTenantModal.js`  
Modal for creating new tenants.
- **Fields**: Name, domain, admin email, OIDC config

#### TabNav
**Path**: `components/TabNav.js`  
Tab navigation (shared pattern with B2B).

---

## 8. B2C Web Components

**Location Base**: `frontend/src/modules/b2c/web/`

### 8.1. Page Components

#### DashboardPage (B2C)
**Path**: `pages/DashboardPage.js`  
User workspace dashboard.
- **Layout**: Top navbar (no sidebar)
- **Features**: Personal workspace, recent activity

#### WorkspacePage
**Path**: `pages/WorkspacePage.js`  
Individual workspace view.

#### LoginPage (B2C)
**Path**: `pages/LoginPage.js`  
B2C user authentication.

#### SignupPage
**Path**: `pages/SignupPage.js`  
B2C user registration.

#### WelcomePage
**Path**: `pages/WelcomePage.js`  
Landing/welcome page for new users.

---

## 9. Shared Core Components

**Location Base**: `frontend/src/core/components/`

### 9.1. Form Components

#### Button
**Path**: `Button.js`  
Reusable button component.
- **Variants**: `primary`, `secondary`, `danger`, `ghost`
- **Sizes**: `sm`, `md`, `lg`
- **Props**: `variant`, `size`, `disabled`, `loading`, `onClick`, `children`

#### Card
**Path**: `Card.js`  
Container card component.
- **Props**: `className`, `children`, `padding`
- **Style**: White background, border, shadow

### 9.2. Feedback Components

#### ImpersonationBanner
**Path**: `ImpersonationBanner.js`  
Warning banner when admin impersonates user.
- **Usage**: B2B admin impersonation feature

#### Toast/Alert
(To be implemented)

---

## 10. Animation & Transition Guidelines

### 10.1. Principles
- **Subtle over showy** - Minimal movement
- **Purposeful** - Only animate what needs feedback
- **Fast** - Keep under 200ms for most interactions
- **No vertical movement** on hover (no translateY transforms)

### 10.2. Standard Transitions
```css
/* Color/Background changes */
transition: background-color 0.15s ease, color 0.15s ease;

/* Sidebar expansion */
transition: width 0.3s ease;

/* Fade in/out */
transition: opacity 0.2s ease;
```

### 10.3. Loading States
- Use skeleton screens (not spinners) for page loads
- Show skeleton immediately (no delay)
- Fade in content when loaded

---

## 11. Responsive Breakpoints

| Breakpoint | Width | Target |
|------------|-------|--------|
| `xs` | < 640px | Mobile portrait |
| `sm` | 640px - 768px | Mobile landscape |
| `md` | 768px - 1024px | Tablet |
| `lg` | 1024px - 1280px | Desktop |
| `xl` | 1280px+ | Large desktop |

---

## 12. Best Practices

### 12.1. Component Usage

**B2B:**
- Always wrap pages in `AdminLayout`
- Use appropriate skeletons for loading states
- Use `RoleBadge` and `TeamRoleBadge` for roles
- Use `StatusBadge` for invitation/user status

**Platform:**
- Wrap pages in `SuperAdminLayout`
- Maintain purple theme distinction
- Use `CreateTenantModal` for tenant creation

**B2C:**
- Use top navbar layout (no sidebar)
- Simpler, cleaner UI
- Focus on user workspace experience

### 12.2. Styling
- Prefer specific transitions over `transition: all`
- Use inline styles sparingly (component-specific only)
- Maintain consistent spacing (multiples of 4px)
- Use design tokens for all colors
- No `translateY` transforms on hover (causes excessive movement)

### 12.3. Accessibility
- All badges have semantic colors
- Minimum touch target: 44x44px (mobile)
- Keyboard navigation support
- Clear focus states
- ARIA labels where appropriate

### 12.4. Performance
- Use CSS-only animations where possible
- Skeleton screens for immediate feedback
- Minimize JavaScript hover states
- Lazy load heavy components

---

## 13. Platform Distinctions

### Visual Hierarchy

| Aspect | B2B | Platform | B2C |
|--------|-----|----------|-----|
| Primary Color | Blue (#4F46E5) | Purple (#8B5CF6) | Indigo (#6366F1) |
| Sidebar | Dark Gray | Purple | None (top nav) |
| Layout | Complex admin | Super admin | Simple user |
| Target User | Tenant admins | Platform ops | End users |

### Feature Complexity

- **B2B**: Most complex - full tenant administration
- **Platform**: Medium - system oversight and tenant management
- **B2C**: Simplest - personal workspace and collaboration

---

## 14. Mobile Components (React Native) 📱

**Status**: Partially implemented

### 14.1. Proposed Components

#### ProfileWidget
**Location**: `frontend/mobile/components/ProfileWidget.tsx` (Proposed)  
Displays user identity and logout action.

#### StatCard (Mobile)
**Location**: `frontend/mobile/components/StatCard.tsx` (Proposed)  
Mobile-optimized version of metrics card.
- **Style**: Surface background, Elevation 2 shadow, Corner Radius 12

#### Button (Mobile)
**Location**: Native Element
- **Primary**: `bg-indigo-600`
- **Secondary**: `bg-white`, `border-gray-300`

---

## 15. Implementation Checklist

### When Adding New Components:

- [ ] Define in appropriate section of this doc
- [ ] Use design tokens (no hardcoded colors)
- [ ] Follow spacing system (4px multiples)
- [ ] Add loading skeleton if needed
- [ ] Implement responsive behavior
- [ ] Test accessibility
- [ ] Document props and usage
- [ ] Add to correct location path

### When Adding New Pages:

- [ ] Use appropriate Layout component
- [ ] Add skeleton for loading state
- [ ] Follow platform-specific styling
- [ ] Implement error states
- [ ] Add to navigation/routing
- [ ] Update this documentation

---

## 16. Future Additions

- Toast/Snackbar notification system
- Modal component library
- Form validation components
- Data visualization components (charts)
- File upload components
- Rich text editor
- Calendar/date picker

---

**Version History:**
- v1.0 (Initial) - Basic B2B components only
- v2.0 (2025-12-16) - Comprehensive coverage of all three platforms (B2B, Platform, B2C)
