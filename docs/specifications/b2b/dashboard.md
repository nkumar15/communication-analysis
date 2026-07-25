# Dashboard Specification

**ID**: `SPEC-DASHBOARD-01`  
**Status**: Draft  
**Last Updated**: 2025-12-12

## 1. Overview

The dashboard provides role-appropriate views for all users. Instead of a one-size-fits-all approach, each role sees relevant information and actions based on their responsibilities and permissions.

## 2. Role Hierarchy

```
Tenant Roles (Organization-wide scope)
├── owner     → Full org visibility, billing, settings
├── admin     → Org management, no billing
├── member    → Team-scoped operations
└── viewer    → Read-only access

Team Roles (Team-scoped)
├── team_manager    → Team administration
├── team_contributor → Create/edit resources
└── team_reader     → View resources only
```

## 3. Dashboard Views by Role

### 3.1 Owner Dashboard
**Focus**: Organization health, strategic overview, billing

| Widget | Description | Priority |
|--------|-------------|----------|
| Org Health Score | Combined metric of usage, activity, health | High |
| User Statistics | Total, active, pending invites | High |
| Team Overview | Teams count, member distribution | High |
| Billing Summary | Current plan, usage, next invoice | High |
| Recent Audit Events | Last 5 security/admin actions | Medium |
| Quick Actions | Invite user, create team, manage billing | High |

### 3.2 Admin Dashboard
**Focus**: User/team management, operational health

| Widget | Description | Priority |
|--------|-------------|----------|
| User Statistics | Total, active, pending invites | High |
| Team Overview | Teams count, member distribution | High |
| Pending Actions | Invitations needing follow-up, pending approvals | High |
| Recent Activity | Last 10 org-wide activities | Medium |
| Quick Actions | Invite user, create team, view audit logs | High |

### 3.3 Member Dashboard
**Focus**: Personal productivity, team context

| Widget | Description | Priority |
|--------|-------------|----------|
| My Teams | Teams user belongs to with role badges | High |
| My Recent Activity | Personal recent actions | Medium |
| Team Highlights | Stats for user's teams (projects, tasks) | High |
| My Tasks | Assigned/created tasks (domain-specific) | High |
| Quick Actions | View projects, create task | Medium |

### 3.4 Viewer Dashboard
**Focus**: Read-only overview, discovery

| Widget | Description | Priority |
|--------|-------------|----------|
| My Teams | Teams user can view | High |
| Organization Overview | High-level stats (read-only) | Medium |
| Recent Updates | Recent changes in visible scope | Medium |
| Quick Navigation | Links to viewable resources | Medium |

## 4. Team Role Overlays

Team roles modify what data is shown **within team-scoped widgets**:

| Team Role | Data Visibility |
|-----------|-----------------|
| team_manager | All team data + team settings + member management |
| team_contributor | All team resources, no settings/member mgmt |
| team_reader | Read-only view of team resources |

## 5. Widget Permission Matrix

| Widget | owner | admin | member | viewer |
|--------|:-----:|:-----:|:------:|:------:|
| Org Health Score | ✅ | ❌ | ❌ | ❌ |
| Billing Summary | ✅ | ❌ | ❌ | ❌ |
| User Statistics | ✅ | ✅ | ❌ | ❌ |
| Team Overview | ✅ | ✅ | 🔵 own | 🔵 own |
| Pending Actions | ✅ | ✅ | ❌ | ❌ |
| Audit Events | ✅ | ✅ | ❌ | ❌ |
| My Teams | ✅ | ✅ | ✅ | ✅ |
| My Tasks | ✅ | ✅ | ✅ | 🔵 read |
| My Recent Activity | ✅ | ✅ | ✅ | ✅ |

Legend: ✅ Full | 🔵 Limited/Scoped | ❌ Hidden

## 6. API Requirements

### 6.1 Dashboard Stats Endpoint
```
GET /api/b2b/dashboard/stats
```
Response varies by role - backend filters data based on user permissions.

### 6.2 Proposed Response Structure
```json
{
  "role": "member",
  "scope": "team",
  "widgets": {
    "my_teams": [...],
    "my_tasks": { "assigned": 5, "overdue": 1 },
    "recent_activity": [...],
    "team_stats": { "projects": 12, "tasks": 45 }
  },
  "quick_actions": ["view_projects", "create_task"]
}
```

## 7. UI/UX Guidelines

### 7.1 Progressive Disclosure
- Don't show empty/forbidden widgets
- Gracefully degrade based on permissions
- Show helpful "upgrade" hints where appropriate

### 7.2 Responsive Layout
```
Desktop: 3-4 column grid
Tablet: 2 column grid
Mobile: 1 column stack
```

### 7.3 Color Coding (per ui-design.md)
- Primary actions: `#4F46E5`
- Success/positive: `#10B981`
- Warning/pending: `#F59E0B`
- Error/overdue: `#EF4444`

## 8. Implementation Phases

### Phase 1: Role Detection & Basic Differentiation
- [ ] Add role-based layout switching
- [ ] Create widget visibility config
- [ ] Implement "My Teams" widget for all roles

### Phase 2: Member/Viewer Experience
- [ ] "My Tasks" widget with team scoping
- [ ] "My Recent Activity" feed
- [ ] Team-specific stats

### Phase 3: Admin/Owner Enhancements
- [ ] Org health score calculation
- [ ] Billing widget (owner only)
- [ ] Enhanced audit log preview

## 9. Confirmed Design Decisions

1. ✅ **Members see org-wide stats** - Total users, teams visible to all roles
2. ✅ **Domain-specific widgets included** - Projects/Tasks widgets integrated
3. ✅ **Notifications integration** - Unread count shown on dashboard
4. ✅ **Customizable dashboard** - Users can reorder/hide widgets

### 9.1 Additional Widgets (Domain-Specific)

| Widget | owner | admin | member | viewer |
|--------|:-----:|:-----:|:------:|:------:|
| My Projects | ✅ | ✅ | ✅ | 🔵 read |
| My Tasks | ✅ | ✅ | ✅ | 🔵 read |
| Overdue Tasks | ✅ | ✅ | ✅ | ❌ |
| Notification Badge | ✅ | ✅ | ✅ | ✅ |

### 9.2 Customization Features

- **Widget Visibility**: Users can show/hide optional widgets
- **Widget Order**: Drag-and-drop reordering
- **Persistence**: Save preferences per user in `user_preferences` table
- **Reset**: Option to restore default layout

---

## Appendix: Current State

The existing `DashboardPage.js` only supports owner/admin with:
- 4 stat cards (total users, active, pending invites, managers)
- Welcome card with feature highlights
- Quick actions (Manage Users, Send Invitation)

All other roles see "Access Denied" message.
