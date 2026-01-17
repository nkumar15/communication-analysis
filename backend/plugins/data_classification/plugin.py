from typing import Dict, Any
from core.rbac.plugin_system import RBACPlugin, PermissionContext
import logging

logger = logging.getLogger(__name__)

class DataClassificationPlugin(RBACPlugin):
    """
    Enforces data classification (Clearance Level vs Sensitivity).
    """
    
    SENSITIVITY_LEVELS = {
        "PUBLIC": 0,
        "INTERNAL": 1,
        "CONFIDENTIAL": 2,
        "RESTRICTED": 3,
        "TOP_SECRET": 4
    }
    
    def get_metadata(self) -> dict:
        return {
            "name": "data_classification",
            "version": "1.0.0",
            "description": "Enforces clearance levels based on data sensitivity"
        }
        
    async def initialize(self, db, config: Dict[str, Any]) -> bool:
        self.config = config
        return True
        
    async def after_permission_check(
        self, context: PermissionContext, core_result: bool, db
    ) -> bool:
        if not core_result:
            return False
            
        # 1. Get Resource Sensitivity
        sensitivity = None
        if context.resource and hasattr(context.resource, 'sensitivity'):
            sensitivity = context.resource.sensitivity
        elif context.extra_context and 'sensitivity' in context.extra_context:
            sensitivity = context.extra_context['sensitivity']
            
        if not sensitivity:
            # Default sensitivity if configured?
            default = self.config.get("default_level", "INTERNAL")
            # If default is applied, user must meet it. 
            # If resource is truely unclassified, maybe we assume PUBLIC?
            # Let's assume strict: if we can't determine, we allow ONLY if not enforcing strict on missing.
            # Plan says "default_level: INTERNAL".
            sensitivity = default
            
        # If sensitivity is string but enum in DB, handle conversion
        if hasattr(sensitivity, 'value'): # Enum
            sensitivity = sensitivity.value
        
        required_level = self.SENSITIVITY_LEVELS.get(str(sensitivity), 1)
        
        # 2. Get User Clearance
        # This assumes 'clearance_level' was enriched onto the user OR is on the user object.
        # User model doesn't have clearance_level, RoleTemplate does.
        # We need to ensure enrich_user_context puts it there, or we fetch it here.
        # The Implementation Plan didn't specify 'enrich_user_context' for this plugin, 
        # but 1.3 says "Update yaml... clearance_level".
        # 3.2 Update Existing Models says RoleTemplate has clearance_level.
        # But User has role_id. We need to fetch the clearance from the role.
        
        user_clearance = context.user.get("clearance_level", 0)
        
        if user_clearance >= required_level:
            return True
            
        logger.info(f"Clearance Deny: User {context.user_id} (Lvl {user_clearance}) vs Resource (Lvl {required_level}/{sensitivity})")
        return False

    async def enrich_user_context(self, user: Dict[str, Any], db) -> Dict[str, Any]:
        """
        Fetch clearance level from the user's role and add to context.
        """
        user_id = user.get("id")
        role_id = user.get("role_id")
        
        if not role_id and user_id:
             # Try to fetch role_id from DB if not in context
             pass 

        if not role_id:
            return {"clearance_level": 1} # Default
            
        # Fetch clearance from Role table
        from sqlalchemy import text
        stmt = text("SELECT clearance_level FROM b2b.roles WHERE id = :role_id")
        result = await db.execute(stmt, {"role_id": role_id})
        row = result.fetchone()
        
        if row:
            return {"clearance_level": row.clearance_level}
            
        return {"clearance_level": 1} 
