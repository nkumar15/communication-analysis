from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class PermissionContext:
    """
    Context passed to permission checks to provide plugins with necessary data.
    """
    user_id: str
    user: Dict[str, Any]
    resource_type: str
    resource_id: Optional[str]
    resource: Optional[Any]
    action: str
    tenant_id: str
    extra_context: Optional[Dict[str, Any]] = None

class RBACPlugin(ABC):
    """
    Abstract base class for all RBAC plugins.
    Plugins can intercept permission checks and enrich user context.
    """
    
    @abstractmethod
    def get_metadata(self) -> dict:
        """
        Return plugin metadata including name and version.
        Example: {"name": "geographic_boundaries", "version": "1.0.0"}
        """
        pass
    
    @abstractmethod
    async def initialize(self, db, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin with configuration.
        """
        pass
    
    async def before_permission_check(
        self, context: PermissionContext, db
    ) -> Optional[bool]:
        """
        Hook called logic BEFORE core permission check.
        Return:
            - True: Grant access immediately (skip core check)
            - False: Deny access immediately (skip core check)
            - None: Continue to core check
        """
        return None

    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        """
        Hook called logic AFTER core permission check.
        Can override or augment the result from the core RBAC check.
        """
        return core_result
    
    async def enrich_user_context(self, user: Dict[str, Any], db) -> Dict[str, Any]:
        """
        Add plugin-specific data to the user object/context.
        Example: Adding 'geographic_scopes' or 'clearance_level'.
        """
        return {}

    async def on_tenant_enable(self, tenant_id: str, db) -> None:
        """
        Lifecycle Hook: Called when a tenant Enables this plugin.
        Use this to seed default data (e.g. Default Regions) or validate dependencies.
        Implementation MUST be Idempotent (safe to run multiple times).
        """
        pass

    async def on_tenant_disable(self, tenant_id: str, db) -> None:
        """
        Lifecycle Hook: Called when a tenant Disables this plugin.
        Use for minimal cleanup or status updates. 
        CRITICAL: Do NOT delete user data by default to prevent data loss on accidental downgrade.
        """
        pass
