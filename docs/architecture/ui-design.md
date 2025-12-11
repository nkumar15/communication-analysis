# UI Design & Components Specification

**ID**: `SPEC-DESIGN-01`
**Status**: Draft
**Scope**: Web Admin, Tenant Dashboard, Mobile App

## 1. Overview
This specification defines the **visual language**, **design tokens**, and **reusable components** for the SaaS platform. All implementations (Web & Mobile) must strictly adhere to these values to ensure brand consistency.

## 2. Design Tokens
Tokens are abstract values that represent design decisions. They must be implemented as constants in code (e.g., JS constants, Swift structs, XML resources), **not** just CSS variables.

### 2.1. Color Palette

**Primary Actions**
- `Primary Blue`: `#4F46E5` (Main actions, Links)
- `Secondary Purple`: `#8B5CF6` (Platform Admin actions)

**Feedback / State**
- `Success Green`: `#10B981` (Success messages, valid states)
- `Warning Orange`: `#F59E0B` (Warnings, pending actions)
- `Error Red`: `#EF4444` (Destructive actions, validation errors)

**Neutrals**
- `Text Primary`: `#111827` (Main content)
- `Text Secondary`: `#6B7280` (Subtitles, placeholders)
- `Border`: `#E5E7EB` (Dividers, input borders)
- `Background`: `#F9FAFB` (Page background)
- `Surface`: `#FFFFFF` (Card/Modal background)

### 2.2. Domain-Specific Colors

**Role Badges**
- `Role Admin`: `#7C3AED` (Purple)
- `Role Manager`: `#D97706` (Orange)
- `Role Member`: `#2563EB` (Blue)

**Status Indicators**
- `Status Active`: `#059669` (Green)
- `Status Inactive`: `#6B7280` (Gray)
- `Status Pending`: `#D97706` (Orange)
- `Status Expired`: `#DC2626` (Red)

## 3. Typography

**Constraint**: Use system fonts where possible for performance, but fallback to Inter.

### 3.1. Scale (Web / Mobile)

| Token | Web Size (px) | Mobile Size (pt) | Weight | Usage |
|-------|---------------|------------------|--------|-------|
| `Heading 1` | 30px | 28pt | Bold (700) | Page Titles |
| `Heading 2` | 24px | 22pt | Semibold (600) | Section Headers |
| `Heading 3` | 20px | 18pt | Medium (500) | Card Titles |
| `Body Large` | 16px | 16pt | Regular (400) | Primary Text |
| `Body Small` | 14px | 14pt | Regular (400) | Secondary Text |
| `Caption`    | 12px | 12pt | Regular (400) | Labels, Badges |

## 4. Layout Guidelines

**Constraint**: Strict separation of layouts for distinct platforms.

### 4.1. Web Layout (Admin Desktop)
- **Grid**: 12-column fluid grid.
- **Sidebar**: Fixed width `250px`.
- **Header**: Fixed height `64px`.
- **Content Padding**: `32px` (2rem).

### 4.2. Mobile Layout (App Flow)
- **Grid**: Single column fluid.
- **Navigation**: Bottom Tab Bar or Stack Navigation.
- **Touch Targets**: Minimum `44x44` points.
- **Safe Area**: Must respect notch/home indicator areas.

## 5. Spacing System
Use these unitless multipliers. Base unit = `4px`.
- `Space-1`: 4px
- `Space-2`: 8px
- `Space-4`: 16px
- `Space-6`: 24px
- `Space-8`: 32px

---

## 6. Web UI Components

### 6.1. Layout Components

#### AdminLayout
**Location**: `frontend/src/components/layout/AdminLayout.js`
Main layout wrapper for all admin pages.
- **Props**: `title`, `subtitle`, `children`

#### Sidebar
**Location**: `frontend/src/components/layout/Sidebar.js`
Fixed left navigation sidebar.
- **Menu Items**: Dashboard, User Management, etc.

#### Header
**Location**: `frontend/src/components/layout/Header.js`
Top header bar with title and user profile.

#### UserProfileDropdown
**Location**: `frontend/src/components/layout/UserProfileDropdown.js`
User profile dropdown menu with Logout.

### 6.2. Utility Components

#### StatCard
**Location**: `frontend/src/components/StatCard.js`
Statistics card for displaying metrics.
- **Props**: `icon`, `label`, `value`, `color`

#### RoleBadge
**Location**: `frontend/src/components/RoleBadge.js`
Color-coded badge for user roles.
- **Roles**: Admin (Purple), Manager (Orange), Member (Blue)

#### StatusBadge
**Location**: `frontend/src/components/StatusBadge.js`
Status indicator badge.
- **Types**: User (Active/Inactive), Invitation (Pending/Accepted/Expired)

#### TabNav
**Location**: `frontend/src/components/TabNav.js`
Tab navigation component.
- **Props**: `tabs` (id, label, count), `activeTab`, `onTabChange`

#### ActionMenu
**Location**: `frontend/src/components/ActionMenu.js`
Three-dot dropdown menu for actions.
- **Props**: `actions` (label, icon, onClick, danger)

## 7. Mobile Components (React Native) 📱

### ProfileWidget
**Location**: `frontend/mobile/components/ProfileWidget.tsx` (Proposed)
Displays user identity and logout action.

### StatCard (Mobile)
**Location**: `frontend/mobile/components/StatCard.tsx` (Proposed)
Mobile-optimized version of the metrics card.
- **Style Tokens**: Surface background, Elevation 2 shadow, Corner Radius 12.

### Button (Mobile)
**Location**: Native Element
- **Primary**: `bg-indigo-600`
- **Secondary**: `bg-white`, `border-gray-300`

## 8. Best Practices

### Component Usage
- Always wrap admin pages in `AdminLayout`
- Use `StatCard` for metrics display
- Use `RoleBadge` and `StatusBadge` for consistency

### Styling
- Use inline styles only when necessary
- Use CSS classes for shared styles
- Maintain consistent spacing (multiples of 4px)
- Use design tokens for colors

### Accessibility
- All badges have semantic colors
- Action menus support keyboard navigation
- Click-outside to close for better UX
- Clear visual feedback on hover
