import logging
from typing import Dict, List, Optional, Any
from core.rbac.plugin_system import RBACPlugin, PermissionContext

logger = logging.getLogger(__name__)

class PluginRegistry:
    """
    Singleton registry to manage RBAC plugins.
    Handles registration, initialization, and execution of plugin hooks.
    """
    
    def __init__(self):
        self._plugins: Dict[str, RBACPlugin] = {}
        # Execution order could be managed here if dependencies arise
        
    def register(self, plugin: RBACPlugin):
        """Register a new plugin."""
        metadata = plugin.get_metadata()
        name = metadata['name']
        
        if name in self._plugins:
            logger.warning(f"Plugin {name} is already registered. Overwriting.")
            
        self._plugins[name] = plugin
        logger.info(f"Registered RBAC plugin: {name} v{metadata.get('version', 'unknown')}")
    
    def get_plugin(self, name: str) -> Optional[RBACPlugin]:
        return self._plugins.get(name)

    async def initialize_all(self, db, config: Dict[str, Any]):
        """Initialize all registered plugins with their specific config."""
        for name, plugin in self._plugins.items():
            plugin_config = config.get(name, {})
            try:
                await plugin.initialize(db, plugin_config)
                logger.info(f"Initialized plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize plugin {name}: {str(e)}")
                # Depending on strictness, we might want to raise here
                
    async def check_permission(
        self, context: PermissionContext, core_checker, db, enabled_plugin_names: Optional[List[str]] = None
    ) -> bool:
        """
        Execute permission check with all plugins.
        Flow:
            1. before_permission_check (Short-circuit)
            2. core_checker (Standard RBAC)
            3. after_permission_check (Override/Filter)
        """
        
        # 1. Pre-Check Hooks
        for name, plugin in self._plugins.items():
            if enabled_plugin_names is not None and name not in enabled_plugin_names:
                continue

            try:
                result = await plugin.before_permission_check(context, db)
                if result is True:
                    return True  # Short-circuit ALLOW
                if result is False:
                    return False  # Short-circuit DENY
            except Exception as e:
                # Fail-safe: security plugin errors must deny, not silently pass.
                logger.error(f"before_permission_check error in plugin '{name}' — failing safe (DENY): {e}", exc_info=True)
                return False

        # 2. Core Check
        core_result = await core_checker(context, db)

        # 3. Post-Check Hooks (can only restrict, never promote)
        final_result = core_result
        for name, plugin in self._plugins.items():
            if enabled_plugin_names is not None and name not in enabled_plugin_names:
                continue

            try:
                final_result = await plugin.after_permission_check(context, final_result, db)
            except Exception as e:
                # Fail-safe: an erroring post-check constraint must deny access.
                logger.error(f"after_permission_check error in plugin '{name}' — failing safe (DENY): {e}", exc_info=True)
                return False

        return final_result
    
    async def enrich_user(self, user: Dict, db, enabled_plugin_names: Optional[List[str]] = None) -> Dict:
        """Enrich user dictionary with plugin data."""
        enriched = user.copy()

        # Let each active plugin verify its sibling dependencies once per enrichment.
        if enabled_plugin_names is not None:
            for name, plugin in self._plugins.items():
                if name in enabled_plugin_names:
                    plugin.check_dependencies(enabled_plugin_names)

        for name, plugin in self._plugins.items():
            if enabled_plugin_names is not None and name not in enabled_plugin_names:
                continue
                
            try:
                plugin_data = await plugin.enrich_user_context(user, db)
                enriched.update(plugin_data)
            except Exception as e:
                logger.error(f"enrich_user_context error in plugin '{name}': {e}", exc_info=True)
                # Mark context as not fully enriched so permission checker re-fetches rather
                # than treating a partial result as complete.
                enriched["context_enriched"] = False
                return enriched
        enriched["context_enriched"] = True
        return enriched

# Global instance
plugin_registry = PluginRegistry()
