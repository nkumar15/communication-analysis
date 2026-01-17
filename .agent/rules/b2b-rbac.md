# B2B RBAC & Plugin Architecture

## Scope
This RBAC model applies specifically to the **B2B (Business-to-Business)** module. It does not apply to Platform or B2C contexts.

## 1. Core Principle: Separation of Identity & Authority
- **Rule**: Distinctly separate **System Roles** (Layer 1) from **Business Roles** (Layer 2).
- **Implementation**:
  - **System Role**: Controls login, billing, and tenant governance.
  - **Business Role**: Controls operational actions and data access within specific teams.
  - **Constraint**: Holding a System Role (even Owner) does **NOT** grant implicit membership or roles within Teams. Access to Team data requires explicit assignment to a Business Role.

## 2. The 3-Layer Permission Model
The architecture extends the standard 2-Layer model with a Plugin Layer for enterprise constraints.

### Layer 1: System Role (Tenant Level)
- **Scope**: Entire Tenant.
- **Roles**: `owner`, `admin`, `member`, `viewer` (Fixed Standard Roles).
- **Responsibility**: Governance, Billing, User Management, and **Team Structure** (Creation/Deletion).

### Layer 2: Business Role (Team Level)
- **Scope**: Single Team (`team_id`).
- **Roles**: Dynamic/Use-Case specific (e.g., `account_manager`, `analyst`, `reviewer`).
- **Responsibility**: Operational workflows (e.g., publishing posts, approving reports).
- **Constraint**: Authority is limited strictly to the assigned team (and its hierarchy if plugins enabled).

### Layer 3: Plugin Constraints (Enterprise Level)
- **Scope**: Cross-cutting constraints (Hierarchy, Geography, Classification).
- **Mechanism**: Interceptors that hook into the permission check flow.
- **Rule**: Plugins can **Short-Circuit** (Allow/Deny early) or **Filter** (Deny late) the core RBAC check.

## 3. Permission Resolution Flow
Correct permission checks **MUST** follow this sequence:
1.  **Plugin Enrichment**: `enrich_user_context()` adds scopes (e.g., `accessible_teams`, `geo_regions`).
2.  **Plugin Before Hook**: `before_permission_check()` runs (e.g., deny if clearance level too low).
3.  **Core RBAC Check**:
    - **System Role Check**: Active?
    - **Tenant Role Check**: Has action permission?
    - **Team Scope Check**: Is member of team?
4.  **Plugin After Hook**: `after_permission_check()` runs (e.g., deny if data region mismatches user region).

## 4. Default Assignment Rules
- **No Implicit Access**: Users are created as `member` with **no** business authority until explicitly assigned a team role.
- **Unassigned State**: An empty team list is the valid "Unassigned" state. usage of a "Default Team" is **FORBIDDEN**.
