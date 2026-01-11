# RBAC Plugin Architecture

**Audience:** Backend Developers  
**Last Updated:** 2026-01-11

This document describes the **Plugin Layer** that extends the 3-Layer RBAC model for enterprise requirements like hierarchical teams, geographic boundaries, and data classification.

---

## Overview

The core 3-Layer RBAC model handles:
- **Layer 1:** System Role (can login?)
- **Layer 2:** Tenant Role (what actions?)
- **Layer 3:** Team (which data?)

For enterprise use cases, additional constraints are needed:
- **Hierarchical Teams:** Director sees child desks without explicit membership
- **Geographic Boundaries:** User can only access data from their region
- **Data Classification:** User clearance must match data sensitivity

These are handled by the **Plugin Layer** - an interceptor-based extension system.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   PERMISSION CHECK FLOW                       │
├──────────────────────────────────────────────────────────────┤
│  1. Plugin: enrich_user_context()                            │
│     → Add geographic_scopes, accessible_teams, clearance     │
│                                                               │
│  2. Plugin: before_permission_check()                         │
│     → Short-circuit: Return True/False to skip core check     │
│                                                               │
│  3. CORE RBAC CHECK (3-Layer Model)                          │
│     → System Role → Tenant Role → Team Scope                  │
│                                                               │
│  4. Plugin: after_permission_check()                          │
│     → Filter/Override result (e.g., geographic deny)          │
└──────────────────────────────────────────────────────────────┘
```

---

## Plugin Interface

All plugins implement the `RBACPlugin` abstract base class:

```python
# backend/core/rbac/plugin_system.py

class RBACPlugin(ABC):
    """Abstract base class for RBAC plugins."""
    
    @abstractmethod
    def get_metadata(self) -> dict:
        """Return plugin name, version, description."""
        pass
    
    @abstractmethod
    async def initialize(self, db, config: Dict[str, Any]) -> bool:
        """Initialize with configuration from plugins.yaml."""
        pass
    
    async def enrich_user_context(self, user: Dict, db) -> Dict[str, Any]:
        """
        Add plugin-specific data to user context.
        Example: Add 'geographic_scopes' or 'accessible_teams'.
        """
        return {}
    
    async def before_permission_check(
        self, context: PermissionContext, db
    ) -> Optional[bool]:
        """
        Hook BEFORE core RBAC check.
        Returns:
            - True: Grant access (skip core check)
            - False: Deny access (skip core check)
            - None: Continue to core check
        """
        return None
    
    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        """
        Hook AFTER core RBAC check.
        Can override or filter the result.
        """
        return core_result
```

---

## Available Plugins

### 1. Hierarchical Teams Plugin

**Purpose:** Allow managers to access child team data without explicit membership.

**Problem Solved:**
- APAC Director manages "SG Desk" and "MY Desk"
- Without plugin: Director needs explicit membership in both
- With plugin: Director auto-inherits access to children of managed teams

**Implementation:**

```python
# backend/plugins/hierarchical_teams/plugin.py

class HierarchicalTeamsPlugin(RBACPlugin):
    async def enrich_user_context(self, user: Dict, db) -> Dict:
        # 1. Get user's direct team memberships
        direct_teams = await self._get_direct_teams_with_roles(user_id, db)
        
        accessible_teams = set()
        
        for team_id, role_name in direct_teams.items():
            accessible_teams.add(team_id)
            
            # 2. If user is a manager, add children
            if role_name in ['surveillance_lead', 'regional_director']:
                children = await self._get_child_teams(team_id, db)
                accessible_teams.update(children)
        
        return {"accessible_teams": list(accessible_teams)}
```

**Configuration:**

```yaml
# plugins.yaml
hierarchical_teams:
  max_depth: 3  # Region → Desk → Unit
  allow_cross_hierarchy: false
```

---

### 2. Geographic Boundaries Plugin

**Purpose:** Restrict access based on user's geographic scope vs data region.

**Problem Solved:**
- User in APAC cannot access EMEA data
- Certain roles (CSO) have global bypass

**Implementation:**

```python
# backend/plugins/geographic_boundaries/plugin.py

class GeographicBoundariesPlugin(RBACPlugin):
    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        if not core_result:
            return False  # Already denied
        
        # 1. Check global role bypass
        if context.user.get("role") in self.config["global_roles"]:
            return True
        
        # 2. Get resource region
        resource_region = context.resource.data_region_id
        
        # 3. Check user scopes
        user_scopes = context.user.get("geographic_scopes", [])
        
        if resource_region in user_scopes:
            return True
        
        return False  # Geographic deny
```

**Configuration:**

```yaml
# plugins.yaml
geographic_boundaries:
  enforce_strict: true
  global_roles: [surveillance_chief, compliance_officer]
  default_regions:
    - code: APAC
      name: Asia Pacific
      regulatory_jurisdiction: MAS
    - code: EMEA
      name: Europe Middle East Africa
      regulatory_jurisdiction: FCA
```

---

### 3. Data Classification Plugin

**Purpose:** Restrict access based on user clearance vs data sensitivity.

**Problem Solved:**
- Top Secret data only visible to users with clearance level 4+
- Prevents junior analysts from seeing executive data

**Configuration:**

```yaml
# plugins.yaml
data_classification:
  enforce_strict: true
  sensitivity_levels:
    - name: PUBLIC
      level: 0
    - name: INTERNAL
      level: 1
    - name: CONFIDENTIAL
      level: 2
    - name: RESTRICTED
      level: 3
    - name: TOP_SECRET
      level: 4
  default_level: INTERNAL
```

---

## Plugin Configuration

Plugins are configured per use case in `plugins.yaml`:

```
backend/scripts/b2b/use_cases/bank_surveillance/plugins.yaml
```

The configuration is loaded during tenant setup and stored in tenant settings.

---

## How Plugins Extend the 3-Layer Model

The 3-Layer model becomes a **4-Layer model** with plugins:

| Layer | Purpose | Example |
|-------|---------|---------|
| **Layer 1:** System Role | Can login? | member, admin, viewer |
| **Layer 2:** Tenant Role | What actions? | surveillance_chief → investigations:approve |
| **Layer 3:** Team | Which team data? | SG Desk, APAC Hub |
| **Layer 4:** Plugins | Enterprise constraints | Geographic, Hierarchy, Classification |

### Permission Resolution with Plugins

```
1. Plugin: Enrich User Context
   → Add accessible_teams (hierarchy), geographic_scopes, clearance_level

2. Plugin: Before Check (optional short-circuit)
   → Example: If clearance < required, deny immediately

3. Core RBAC Check (3-Layer)
   → System Role → Tenant Role Permissions → Team Membership

4. Plugin: After Check (filter/override)
   → Example: Even if core allows, deny if geographic mismatch
```

---

## Plugin Registration

Plugins are registered in `init_plugins.py`:

```python
# backend/core/rbac/init_plugins.py

from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.data_classification.plugin import DataClassificationPlugin

AVAILABLE_PLUGINS = {
    "hierarchical_teams": HierarchicalTeamsPlugin,
    "geographic_boundaries": GeographicBoundariesPlugin,
    "data_classification": DataClassificationPlugin,
}

async def initialize_plugins(tenant_id: UUID, db: AsyncSession):
    """Load and initialize plugins based on tenant config."""
    config = await get_plugin_config(tenant_id, db)
    
    for plugin_name, plugin_class in AVAILABLE_PLUGINS.items():
        if plugin_name in config:
            plugin = plugin_class()
            await plugin.initialize(db, config[plugin_name])
            plugin_registry.register(plugin)
```

---

## Creating a Custom Plugin

1. Create plugin directory:
   ```
   backend/plugins/my_custom_plugin/
   ├── __init__.py
   └── plugin.py
   ```

2. Implement the plugin:
   ```python
   from core.rbac.plugin_system import RBACPlugin, PermissionContext
   
   class MyCustomPlugin(RBACPlugin):
       def get_metadata(self):
           return {"name": "my_custom", "version": "1.0.0"}
       
       async def initialize(self, db, config):
           self.config = config
           return True
       
       async def before_permission_check(self, context, db):
           # Custom logic
           return None  # Continue to core check
   ```

3. Register in `init_plugins.py`

4. Add configuration to `plugins.yaml`

---

## Related Documentation

- [Authorization Architecture](./authorization.md) - 3-Layer RBAC core
- [RBAC Concepts Guide](../../guides/b2b-rbac-concepts.md) - Overview and golden rules
- [Bank Surveillance Use Case](../../../backend/scripts/b2b/use_cases/bank_surveillance/README.md) - Enterprise example
