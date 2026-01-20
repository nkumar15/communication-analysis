# RBAC Technical Specification & Feature Guide

**Target Audience:** Backend Developers & Architects  
**Scope:** B2B Module (Core + Enterprise Plugins)

## 1. Overview: The 3-Layer permission Model

The B2B module uses a **3-Layer RBAC Model** to handle complex enterprise requirements (Tenants, Teams, Geographies, Data Sensitivity) while keeping the core simple.

| Layer | Type | Responsibility | Example | Source of Data |
|-------|------|----------------|---------|----------------|
| **1** | **System Role** | Authentication & Billing | `tenant_owner` vs `member` | `users` table |
| **2** | **Business Role** | Functional Access | `surveillance_analyst` (Team Scope) | `team_members` table |
| **3** | **Plugin Layer** | Enterprise Constraints | `geographic_boundaries` (APAC-only) | `plugin_hooks` |

---

## 2. Permission Check Flow

The decisioning flow moves from global context down to specific data attributes.

```mermaid
graph TD
    Request[API Request] -->|Middleware| Auth{Authenticated?}
    Auth -- No --> 401[401 Unauthorized]
    Auth -- Yes --> Router[Endpoint Handler]
    
    subgraph "RBAC Service Decisioning"
        Router -->|check_permission()| PluginPre[1. Plugin: Enrich Context]
        PluginPre -->|Geo, Hierarchy| Context[Full User Context]
        
        Context -->|2. Plugin: Pre-Check| ShortCircuit{Deny Now?}
        ShortCircuit -- Yes --> 403[403 Forbidden]
        
        ShortCircuit -- No --> CoreCheck[3. Core RBAC Check]
        CoreCheck -->|System/Tenant/Team Matching| CoreResult{Allow?}
        CoreResult -- No --> 403
        
        CoreResult -- Yes --> PluginPost[4. Plugin: Post-Check]
        PluginPost -->|Region Mismatch?| FinalDecision{Final Allow?}
        FinalDecision -- No --> 403
        FinalDecision -- Yes --> 200[Grant Access]
    end
```

### Data Sources for Decisioning

1.  **Identity Context** (`current_user`):
    - **System Role**: From JWT / DB (`users.role`).
    - **Tenant ID**: From Hostname/Header (`x-tenant-id`).
    
2.  **Functional Context** (`team_members`):
    - **Team Roles**: Loaded for the specific tenant.
    - **Scope**: Does the user belong to the team owning the resource?

3.  **Plugin Context** (`enriched_context`):
    - **Geographic Scope**: Injected by `GeographicBoundariesPlugin`.
    - **Hierarchy Access**: Injected by `HierarchicalTeamsPlugin` (access to child teams).

---

## 3. Plugin Architecture

Plugins are **interceptors** that hook into the permission lifecycle.

### Interface `RBACPlugin`

```python
class RBACPlugin(ABC):
    async def enrich_user_context(self, user: Dict, db) -> Dict:
        """Add attributes like 'accessible_teams' or 'geographic_scopes'"""
        pass

    async def before_permission_check(self, context, db) -> Optional[bool]:
        """Short-circuit: Return False to DENY immediately before core check"""
        pass

    async def after_permission_check(self, context, core_result, db) -> bool:
        """Filter: Return False to DENY even if core check passed"""
        pass
```

### Available Plugins

#### A. Hierarchical Teams
**Problem**: A Regional Director needs to see cases from all desks under them, without being an explicit member of every single desk.
**Solution**:
- **Enrich**: logic finds all child teams of the user's teams.
- **Result**: User gets access to `team_id: [1, 2, 3]` (explicit + implicit).

#### B. Geographic Boundaries
**Problem**: An "APAC Analyst" must not access "EMEA" data, even if they have the `read:cases` permission.
**Solution**:
- **Post-Check**:
    - Validates `user.geographic_scopes` (e.g., `['APAC']`).
    - Against `resource.data_region` (e.g., `EMEA`).
    - If mismatch -> **DENY**.

#### C. Data Classification
**Problem**: "Confidential" reports should not be visible to "Junior" staff.
**Solution**:
- **Pre-Check**:
    - Checks `user.clearance_level` (e.g., 2).
    - Checks `resource.sensitivity` (e.g., 3).
    - If user < resource -> **DENY**.

---

## 4. Dependencies & Configuration

### Dependencies
- **Middleware**: `core.middleware.authentication` (Sets up `request.state.user`)
- **Service**: `modules.b2b.services.rbac_service` (Orchestrator)
- **Database**:
    - `tenant_settings`: Stores enabled plugins list per tenant.
    - `b2b.teams`: Stores hierarchy (`parent_team_id`).
    - `b2b.geographic_regions`: Stores region definitions.

### Configuration Example
Plugins are configured via `plugins.yaml` and loaded into `tenant_settings` JSONB column.

```yaml
# scripts/b2b/use_cases/bank_surveillance/plugins.yaml

hierarchical_teams:
  max_depth: 3

geographic_boundaries:
  enforce_strict: true
  global_roles: ["surveillance_chief"]  # Bypass for CSO
  default_regions:
    - code: "APAC"
    - code: "EMEA"

data_classification:
  enforce_strict: true
  sensitivity_levels:
    - name: "TOP_SECRET"
      level: 4
```

## 5. Development Guidelines

1.  **Keep Plugins Stateless**: Logic should rely on the `db` session and `context` passed in.
2.  **Fail Safe**: If a plugin errors, it should log and default to **DENY** (Secure by Default).
3.  **Performance**: `enrich_user_context` runs on every request. Cache aggressive lookups (e.g., team hierarchy) in Redis.
