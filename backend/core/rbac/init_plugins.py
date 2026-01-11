import os
import yaml
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

# Import Registry
from core.rbac.plugin_registry import plugin_registry

# Import Plugins
from plugins.hierarchical_teams.plugin import HierarchicalTeamsPlugin
from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin
from plugins.data_classification.plugin import DataClassificationPlugin

logger = logging.getLogger(__name__)

async def initialize_plugins(db: AsyncSession):
    """
    Load plugins based on RBAC_PLUGINS env var and plugins.yaml config.
    """
    enabled_plugins_str = os.getenv("RBAC_PLUGINS", "")
    if not enabled_plugins_str:
        logger.info("No RBAC plugins enabled.")
        return

    enabled_plugins = [p.strip() for p in enabled_plugins_str.split(",") if p.strip()]
    
    # 1. Register Plugins
    # We could implement dynamic loading, but manual registration is safer/simpler for now
    available_plugins = {
        "hierarchical_teams": HierarchicalTeamsPlugin(),
        "geographic_boundaries": GeographicBoundariesPlugin(),
        "data_classification": DataClassificationPlugin(),
    }
    
    for name in enabled_plugins:
        if name in available_plugins:
            plugin_registry.register(available_plugins[name])
        else:
            logger.warning(f"Unknown plugin enabled: {name}")

    # 2. Load Configuration
    # Ideally load from plugins.yaml
    config = {}
    try:
        # Assuming path relative to backend root or configured location
        # Plan says: backend/scripts/b2b/use_cases/bank_surveillance/plugins.yaml
        # But that's specific to the use case. In prod, we'd have a standard config location.
        # For this demo/task, we'll try to load that specific file if it exists, or a default.
        
        # Hardcoding path for the "Bank Surveillance" context of this task
        config_path = "backend/scripts/b2b/use_cases/bank_surveillance/plugins.yaml"
        if os.path.exists(config_path):
             with open(config_path, 'r') as f:
                 config = yaml.safe_load(f)
        else:
            logger.warning(f"Plugin config not found at {config_path}, using defaults")
            
    except Exception as e:
        logger.error(f"Failed to load plugin config: {e}")

    # 3. Initialize Registry
    await plugin_registry.initialize_all(db, config)
