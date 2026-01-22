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
    
    async def enrich_user_context(self, user: Dict[str, Any], db) -> Dict[str, Any]:
        """
        Enrich user with geographical scopes and team-level roles.
        """
        user_id = user.get("id")
        if not user_id:
            return {}
            
        from sqlalchemy import text
        
        # 1. Get Region Codes and Team Role Names
        stmt = text("""
            SELECT DISTINCT 
                t.config_data ->> 'region_code' as code,
                trd.name as role_name
            FROM b2b.team_members tm
            JOIN b2b.teams t ON tm.team_id = t.id
            LEFT JOIN b2b.team_role_definitions trd ON tm.team_role_id = trd.id
            WHERE tm.user_id = :user_id
        """)
        
        result = await db.execute(stmt, {"user_id": user_id})
        rows = result.all()
        
        codes = [row.code for row in rows if row.code]
        team_role_names = [row.role_name for row in rows if row.role_name]
        
        # 2. Resolve Codes to UUIDs (GeographicRegion.id)
        tenant_id = user.get("tenant_id")
        region_ids = []
        if codes and tenant_id:
            stmt_regions = text("""
                SELECT id FROM b2b.geographic_regions
                WHERE tenant_id = :tenant_id
                AND code = ANY(:codes)
            """)
            region_result = await db.execute(stmt_regions, {"tenant_id": tenant_id, "codes": codes})
            region_ids = [str(row.id) for row in region_result]
        
        logger.info(f"Geographic Enrichment for {user_id}: Codes={codes}, TeamRoles={team_role_names} -> IDs={region_ids}")
        
        return {
            "geographic_scopes": region_ids,
            "team_roles": team_role_names # Redundant if already enriched by main checker, but safe for isolation
        }

    
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
        
        # Check Tenant Role
        current_tenant_role = context.user.get("role")
        if current_tenant_role in global_roles:
            return True

        # Check Team Roles (Business Roles)
        current_team_roles = context.user.get("team_roles", [])
        for tr in current_team_roles:
            if tr in global_roles:
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
