import logging
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
    Register and initialize all RBAC plugins.
    
    Plugin configuration is loaded from the seeded `PluginTemplate` table
    in the database by each plugin's `initialize()` method.
    """
    # 1. Register All Available Plugins
    available_plugins = {
        "hierarchical_teams": HierarchicalTeamsPlugin(),
        "geographic_boundaries": GeographicBoundariesPlugin(),
        "data_classification": DataClassificationPlugin(),
    }
    
    for name, plugin in available_plugins.items():
        plugin_registry.register(plugin)

    # 2. Initialize All Plugins (each plugin loads its own config from DB)
    await plugin_registry.initialize_all(db, config={})
    logger.info("All RBAC plugins initialized from database configuration.")

