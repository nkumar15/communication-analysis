from typing import Dict, Any, List
from core.rbac.plugin_system import RBACPlugin, PermissionContext
import logging

logger = logging.getLogger(__name__)

class GeographicBoundariesPlugin(RBACPlugin):
    """
    Enforces geographic access control.
    User must have the resource's 'data_region_id' in their 'geographic_scopes'.
    """
    
    def get_metadata(self) -> dict:
        return {
            "name": "geographic_boundaries",
            "version": "1.0.0",
            "description": "Enforces geographic boundaries on resources"
        }
    
    async def initialize(self, db, config: Dict[str, Any]) -> bool:
        self.config = config
        return True
    
    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        """
        Filter access based on geography.
        Returns False (Deny) if geographic mismatch, even if core_result is True.
        """
        if not core_result:
            return False
            
        # 1. Check Global Role Bypass
        user_role = context.user.get("role_name") # Assumes enriched or available
        # Fallback if role_name not directly in context.user dict, might need to be fetched or passed
        # Setup: Ensure 'role_name' is passed in user dict or we fetch it.
        # For now, let's assume context.user has 'role' which is the name (legacy) or we check role_id.
        # Implementation Plan assumes context.user is dict.
        
        global_roles = self.config.get("global_roles", [])
        # Checking against both 'role' (legacy string) and potentially joined role name
        current_role = context.user.get("role") 
        # If RBAC is fully migrated, context.user might have 'role_obj' or similar. 
        # Checking plain 'role' string for compatibility.
        
        if current_role in global_roles:
            return True

        if context.extra_context and context.extra_context.get("bypass_geographic_restrictions"):
             return True
             
        # 2. Check Resource Region
        resource = context.resource
        region_id = None
        
        if resource and hasattr(resource, 'data_region_id'):
            region_id = resource.data_region_id
        elif context.extra_context and 'data_region_id' in context.extra_context:
            region_id = context.extra_context['data_region_id']
            
        if not region_id:
            return True # No region on resource, allow.
            
        # 3. Check User Scopes
        user_scopes = context.user.get("geographic_scopes", [])
        # scopes are UUIDs. 
        
        if str(region_id) in [str(s) for s in user_scopes]:
            return True
            
        if self.config.get("enforce_strict", True):
            logger.info(f"Geographic Deny: User {context.user_id} scope {user_scopes} vs Region {region_id}")
            return False
            
        return True

    async def on_tenant_enable(self, tenant_id: str, db) -> None:
        """
        Lifecycle hook when plugin is enabled.
        Configuration is now strictly driven by external sources (CLI/YAML) 
        or Admin API, so we do not seed hardcoded defaults here.
        """
        logger.info(f"Plugin Hook: Enabling geographic_boundaries for {tenant_id}")
        # Logic moved to tenant_onboard.py (seed_plugin_config_from_yaml)
        pass



    async def on_tenant_disable(self, tenant_id: str, db) -> None:
        logger.info(f"Plugin Hook: Disabling geographic_boundaries for {tenant_id} (No data purge)")
