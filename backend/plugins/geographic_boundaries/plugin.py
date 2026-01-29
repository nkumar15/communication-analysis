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
        """
        Initialize plugin with configuration.
        Falls back to database template if runtime config is empty.
        """
        self.config = config
        
        # Fallback: If config is empty (e.g. Docker env without mounted scripts), 
        # load from seeded PluginTemplate in DB.
        if not self.config or not self.config.get("global_roles"):
            await self._load_config_from_db(db)
            
        return True

    async def _load_config_from_db(self, db):
        """Helper to load configuration from the database Template."""
        from sqlalchemy import select
        from modules.b2b.models.plugin_template import PluginTemplate
        
        try:
            stmt = select(PluginTemplate).where(PluginTemplate.plugin_slug == "geographic_boundaries")
            result = await db.execute(stmt)
            template = result.scalar_one_or_none()
            
            if template and template.template_data:
                 # Simple merge: DB config is base, passed config overrides
                 self.config = {**template.template_data, **self.config}
                 logger.info(f"Loaded geographic_boundaries config from DB Template.")
        except Exception as e:
            logger.error(f"Failed to load plugin template from DB: {e}")

    def _is_global_user(self, context: PermissionContext) -> bool:
        """
        Check if user should bypass geographic restrictions.
        Checks both Tenant Roles (System) and Team Roles (Business).
        """
        global_roles = self.config.get("global_roles", [])
        if not global_roles:
            return False

        # 1. Check Tenant Role (e.g., 'owner', 'admin')
        if context.user.get("role") in global_roles:
            return True

        # 2. Check Team Roles (e.g., 'surveillance_chief')
        # This relies on enrich_user_context having populated 'team_roles'
        user_team_roles = context.user.get("team_roles", [])
        for role in user_team_roles:
            if role in global_roles:
                return True
                
        # 3. Check explicit bypass flag in context
        if context.extra_context and context.extra_context.get("bypass_geographic_restrictions"):
            return True

        return False

    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        """
        Filter access based on geography.
        Returns False (Deny) if geographic mismatch, even if core_result is True.
        """
        # If core RBAC denied it, we don't need to check geography
        if not core_result:
            return False
            
        # 1. Global Bypass Check (Chief / Compliance Officer)
        if self._is_global_user(context):
            return True
             
        # 2. Check Resource Region
        # Resources must have 'data_region_id' attribute or pass it in extra_context
        resource = context.resource
        region_id = None
        
        if resource and hasattr(resource, 'data_region_id'):
            region_id = resource.data_region_id
        elif context.extra_context and 'data_region_id' in context.extra_context:
            region_id = context.extra_context['data_region_id']
            
        # If resource has no region, it's global data -> Allow
        if not region_id:
            return True 
            
        # 3. Check User Scopes
        # User must have a scope matching the resource's region
        user_scopes = context.user.get("geographic_scopes", [])
        
        if str(region_id) in [str(s) for s in user_scopes]:
            return True
            
        # STRICT ENFORCEMENT: Deny if no matching scope
        if self.config.get("enforce_strict", True):
            logger.info(f"Geographic Deny: User {context.user_id} scope {user_scopes} vs Region {region_id}")
            return False
            
        return True

    async def on_tenant_enable(self, tenant_id: str, db) -> None:
        """
        Lifecycle hook when plugin is enabled.
        Fetches the master template from b2b.plugin_templates and clones it for this tenant.
        """
        from sqlalchemy import select
        from modules.b2b.models.plugin_template import PluginTemplate
        from modules.b2b.models.geographic_region import GeographicRegion
        from uuid import UUID

        logger.info(f"Plugin Hook: Enabling geographic_boundaries for {tenant_id}")
        
        # 1. Fetch Master Template
        stmt = select(PluginTemplate).where(PluginTemplate.plugin_slug == "geographic_boundaries")
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            logger.warning(f"No master template found for geographic_boundaries. Skipping default seed.")
            return

        # 2. Clone/Insert Regions
        regions_data = template.template_data.get('default_regions', [])
        for r in regions_data:
            # Check if already exists (idempotent)
            stmt_check = select(GeographicRegion).where(
                GeographicRegion.tenant_id == UUID(tenant_id),
                GeographicRegion.code == r['code']
            )
            existing = (await db.execute(stmt_check)).scalar_one_or_none()
            
            if not existing:
                new_region = GeographicRegion(
                    tenant_id=UUID(tenant_id),
                    name=r['name'],
                    code=r['code'],
                    regulatory_jurisdiction=r.get('regulatory_jurisdiction'),
                    data_residency_rules=r.get('data_residency_rules')
                )
                db.add(new_region)
                logger.info(f"   + Cloned Region: {r['code']}")
        
        await db.flush()

    async def on_tenant_disable(self, tenant_id: str, db) -> None:
        logger.info(f"Plugin Hook: Disabling geographic_boundaries for {tenant_id} (No data purge)")
