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
    # 1. Register All Available Plugins
    # We register all known plugins so they can be activated per-tenant via DB
    available_plugins = {
        "hierarchical_teams": HierarchicalTeamsPlugin(),
        "geographic_boundaries": GeographicBoundariesPlugin(),
        "data_classification": DataClassificationPlugin(),
    }
    
    for name, plugin in available_plugins.items():
        plugin_registry.register(plugin)

    # 2. Load Configuration
    config = {}
    try:
        # Check potential paths for config (Docker vs Local)
        # 1. Docker: /app/scripts/... -> scripts/...
        # 2. Local: backend/scripts/...
        paths_to_check = [
            "scripts/b2b/use_cases/bank_surveillance/plugins.yaml",
            "backend/scripts/b2b/use_cases/bank_surveillance/plugins.yaml"
        ]
        
        config_path = None
        for p in paths_to_check:
            if os.path.exists(p):
                config_path = p
                break
        
        if config_path:
             logger.info(f"Loading plugin config from {config_path}")
             with open(config_path, 'r') as f:
                 config = yaml.safe_load(f)
        else:
            logger.warning("Plugin config not found in standard locations, using defaults")
            
    except Exception as e:
        logger.error(f"Failed to load plugin config: {e}")

    # 3. Initialize Registry
    await plugin_registry.initialize_all(db, config)
