# UI Components Documentation

Documentation for reusable UI components in the admin dashboard.

---

## Layout Components

### AdminLayout
**Location**: `frontend/src/components/layout/AdminLayout.js`

Main layout wrapper for all admin pages.

**Props:**
- `title` (string) - Page title shown in header
- `subtitle` (string) - Page subtitle/description
- `children` (ReactNode) - Page content

**Usage:**
```jsx
<AdminLayout title="Page Title" subtitle="Description">
  <YourPageContent />
</AdminLayout>
```

---

### Sidebar
**Location**: `frontend/src/components/layout/Sidebar.js`

Fixed left navigation sidebar.

**Features:**
- Logo and branding
- Navigation menu items
- Active state highlighting
- Hover effects

**Menu Items:**
- Dashboard (`/dashboard`)
- User Management (`/invitations`)

---

### Header
**Location**: `frontend/src/components/layout/Header.js`

Top header bar with title and user profile.

**Props:**
- `title` (string) - Main heading
- `subtitle` (string) - Subheading

---

### UserProfileDropdown
**Location**: `frontend/src/components/layout/UserProfileDropdown.js`

User profile dropdown menu.

**Features:**
- User avatar with initials
- Name and role display
- Organization name
- Logout button
- Click-outside to close

---

## Utility Components

### StatCard
**Location**: `frontend/src/components/StatCard.js`

Statistics card for displaying metrics.

**Props:**
- `icon` (string) - Emoji icon
- `label` (string) - Card label
- `value` (number) - Metric value
- `color` (string) - Hex color for accent

**Usage:**
```jsx
<StatCard 
  icon="👥" 
  label="Total Users" 
  value={42} 
  color="#4F46E5" 
/>
```

---

### RoleBadge
**Location**: `frontend/src/components/RoleBadge.js`

Color-coded badge for user roles.

**Props:**
- `role` (string) - 'admin', 'manager', or 'member'

**Colors:**
- Admin: Purple (#7C3AED)
- Manager: Orange (#D97706)
- Member: Blue (#2563EB)

**Usage:**
```jsx
<RoleBadge role="admin" />
```

---

### StatusBadge
**Location**: `frontend/src/components/StatusBadge.js`

Status indicator badge.

**Props:**
- `status` (boolean|string) - Status value
- `type` (string) - 'user' or 'invitation'

**For Users (type='user'):**
- `status={true}` → Green "Active"
- `status={false}` → Gray "Inactive"

**For Invitations (type='invitation'):**
- `status="pending"` → Orange "Pending"
- `status="accepted"` → Green "Accepted"
- `status="expired"` → Red "Expired"

**Usage:**
```jsx
<StatusBadge status={true} type="user" />
<StatusBadge status="pending" type="invitation" />
```

---

### TabNav
**Location**: `frontend/src/components/TabNav.js`

Tab navigation component.

**Props:**
- `tabs` (array) - Array of tab objects
  - `id` (string) - Tab identifier
  - `label` (string) - Tab display text
  - `count` (number, optional) - Badge count
- `activeTab` (string) - Currently active tab ID
- `onTabChange` (function) - Callback when tab changes

**Usage:**
```jsx
<TabNav 
  tabs={[
    { id: 'users', label: 'Users', count: 10 },
    { id: 'invitations', label: 'Invitations', count: 5 }
  ]}
  activeTab={activeTab}
  onTabChange={setActiveTab}
/>
```

---

### ActionMenu
**Location**: `frontend/src/components/ActionMenu.js`

Three-dot dropdown menu for actions.

**Props:**
- `actions` (array) - Array of action objects
  - `label` (string) - Action text
  - `icon` (string, optional) - Emoji icon
  - `onClick` (function) - Click handler
  - `danger` (boolean, optional) - Red text for dangerous actions

**Usage:**
```jsx
<ActionMenu 
  actions={[
    { 
      label: 'Edit', 
      icon: '✏️', 
      onClick: () => console.log('Edit') 
    },
    { 
      label: 'Delete', 
      icon: '🗑️', 
      onClick: () => console.log('Delete'),
      danger: true 
    }
  ]}
/>
```

---

## Design Tokens

## Design Tokens

> [!NOTE]
> **Source of Truth**: All design tokens (Colors, Typography, Layout) are strictly defined in [`docs/specifications/ui-design.md`](../specifications/ui-design.md).
>
> Refer to that document for:
> - Color Palette (Hex codes)
> - Role & Status Colors
> - Typography Scale
> - Spacing Units


---

## Best Practices

### Component Usage
- Always wrap admin pages in `AdminLayout`
- Use `StatCard` for metrics display
- Use `RoleBadge` and `StatusBadge` for consistency
- Use `TabNav` for multi-view pages
- Use `ActionMenu` for row-level actions

### Styling
- Use inline styles for component-specific styling
- Use CSS classes for shared styles
- Maintain consistent spacing (multiples of 4px)
- Use design tokens for colors

### Accessibility
- All badges have semantic colors
- Action menus support keyboard navigation
- Click-outside to close for better UX
- Clear visual feedback on hover

---


## Mobile Components (React Native) 📱

### ProfileWidget
**Location**: `frontend/mobile/components/ProfileWidget.tsx` (Proposed)

Displays user identity and logout action.

**Props:**
- `user` (object) - User data `{ name, email, avatarUrl }`
- `onLogout` (function) - Callback for logout

**Structure:**
- Avatar Image (Left)
- Name/Email Text (Center)
- Logout Icon (Right)

### StatCard (Mobile)
**Location**: `frontend/mobile/components/StatCard.tsx` (Proposed)

Mobile-optimized version of the metrics card.

**Props:**
- `label` (string)
- `value` (string/number)
- `trend` (string, optional)

**Style Tokens:**
- Background: `Surface`
- Shadow: `elevation: 2`
- Corner Radius: `12`

### Button (Mobile)
**Location**: Native Element

**Standard Styles:**
- **Primary**: `bg-indigo-600`, `text-white`, `rounded-lg`, `h-[48px]`
- **Secondary**: `bg-white`, `border-gray-300`, `text-gray-700`

