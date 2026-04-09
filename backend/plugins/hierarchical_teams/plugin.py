from typing import Dict, Any, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.rbac.plugin_system import RBACPlugin, PermissionContext
import logging

logger = logging.getLogger(__name__)

class HierarchicalTeamsPlugin(RBACPlugin):
    """
    RABC Plugin for Hierarchical Teams.
    
    Logic:
    1. During user context enrichment, it finds all teams the user manages.
    2. It then recursively finds all child teams of those managed teams.
    3. It adds these child teams to the 'accessible_teams' list in the user context.
    
    This allows a "Regional Director" (Manager of APAC) to automatically have access 
    to "SG Desk" (Child of APAC) without explicit membership.
    """
    
    def get_metadata(self) -> dict:
        return {
            "name": "hierarchical_teams",
            "version": "1.0.0",
            "description": "Enables recursive access for team hierarchies"
        }
    
    async def initialize(self, db: AsyncSession, config: Dict[str, Any]) -> bool:
        self.config = config
        return True
    
    async def enrich_user_context(self, user: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Enrich User with 'accessible_teams' containing direct memberships + child teams of managed teams.
        
        A user gets child team access if:
        1. They are a tenant-level admin (owner/admin role)
        2. OR their team role has 'team_members:manage' permission (database-driven)
        """
        user_id = user.get("id")
        if not user_id:
            return {}

        # Get direct team memberships with role permissions
        direct_teams = await self._get_direct_teams_with_permissions(user_id, db)
        
        accessible_teams = set()
        
        for team_id, has_manage_permission in direct_teams.items():
            accessible_teams.add(team_id)
            
            # Check if user can manage this team (and thus access children)
            is_manager = False
            
            # Tenant-level admin bypass
            if user.get("role") in ["owner", "admin"]:
                is_manager = True
            # Database-driven: role has team_members:manage permission
            elif has_manage_permission:
                is_manager = True
            
            if is_manager:
                children = await self._get_child_teams(team_id, db)
                accessible_teams.update(children)

        return {"accessible_teams": list(accessible_teams)}

    async def _get_direct_teams_with_permissions(self, user_id: str, db: AsyncSession) -> Dict[str, bool]:
        """
        Returns {team_id: has_manage_permission} for user's direct memberships.
        
        Database-driven permission check: looks for 'team_members:manage' or 'team_members:admin'
        in the team role's permissions JSONB field.
        """
        stmt = text("""
            SELECT 
                tm.team_id,
                trd.permissions as role_permissions
            FROM b2b.team_members tm
            LEFT JOIN b2b.team_role_definitions trd ON tm.team_role_id = trd.id
            WHERE tm.user_id = :user_id
        """)
        result = await db.execute(stmt, {"user_id": user_id})
        
        teams_with_permissions = {}
        for row in result:
            team_id = str(row.team_id)
            permissions = row.role_permissions or []
            
            # Check if role has team_members:manage or team_members:admin permission
            has_manage = False
            for perm in permissions:
                resource = perm.get("resource", "")
                actions = perm.get("actions", [])
                if resource == "team_members" and ("manage" in actions or "admin" in actions):
                    has_manage = True
                    break
            
            teams_with_permissions[team_id] = has_manage
        
        return teams_with_permissions

    async def _get_direct_teams_with_roles(self, user_id: str, db: AsyncSession) -> Dict[str, str]:
        """
        Returns {team_id: role_name} for user's direct memberships.
        DEPRECATED: Use _get_direct_teams_with_permissions for database-driven checks.
        """
        stmt = text("""
            SELECT tm.team_id, trd.name as role_name 
            FROM b2b.team_members tm
            LEFT JOIN b2b.team_role_definitions trd ON tm.team_role_id = trd.id
            WHERE tm.user_id = :user_id
        """)
        result = await db.execute(stmt, {"user_id": user_id})
        return {str(row.team_id): row.role_name for row in result}

    async def _get_child_teams(self, parent_team_id: str, db: AsyncSession) -> List[str]:
        """
        Recursively find all child teams using a recursive CTE.
        CYCLE guard: tracks visited IDs to prevent infinite loops on circular
        parent_team_id relationships (PostgreSQL 14+ CYCLE clause not used for
        broader compatibility; UNION — not UNION ALL — deduplicates instead).
        """
        stmt = text("""
            WITH RECURSIVE team_tree AS (
                SELECT id
                FROM b2b.teams
                WHERE parent_team_id = :parent_id
                  AND id != :parent_id

                UNION

                SELECT t.id
                FROM b2b.teams t
                JOIN team_tree tt ON t.parent_team_id = tt.id
                WHERE t.id != :parent_id
            )
            SELECT id FROM team_tree
        """)

        result = await db.execute(stmt, {"parent_id": parent_team_id})
        return [str(row.id) for row in result]

    async def on_tenant_enable(self, tenant_id: str, db) -> None:
        """
        Lifecycle hook when plugin is enabled.
        Fetches the master template from b2b.plugin_templates and clones it for this tenant.
        """
        from sqlalchemy import select
        from modules.b2b.models.plugin_template import PluginTemplate
        from modules.b2b.models.scope_level import OrgTier
        from uuid import UUID

        logger.info(f"Plugin Hook: Enabling hierarchical_teams for {tenant_id}")
        
        # 1. Fetch Master Template
        stmt = select(PluginTemplate).where(PluginTemplate.plugin_slug == "hierarchical_teams")
        result = await db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if not template:
            logger.warning(f"No master template found for hierarchical_teams. Skipping default seed.")
            return

        # 2. Clone/Insert Org Tiers
        tier_data = template.template_data.get('org_tiers', [])
        for tier in tier_data:
            # Check if already exists (idempotent)
            stmt_check = select(OrgTier).where(
                OrgTier.tenant_id == UUID(tenant_id),
                OrgTier.name == tier['name']
            )
            existing = (await db.execute(stmt_check)).scalar_one_or_none()
            
            if not existing:
                new_tier = OrgTier(
                    tenant_id=UUID(tenant_id),
                    name=tier['name'],
                    display_name=tier['display_name'],
                    description=tier.get('description'),
                    hierarchy_order=tier['hierarchy_order']
                )
                db.add(new_tier)
                logger.info(f"   + Cloned Org Tier: {tier['name']}")
        
        await db.flush()

    async def on_tenant_disable(self, tenant_id: str, db) -> None:
        logger.info(f"Plugin Hook: Disabling hierarchical_teams for {tenant_id} (No data purge)")
