"""
Domain-Specific Scope Helpers for Farming

Farmer access control based on hierarchical roles and teams.
"""
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.b2b.models import UserModel, Role
from services.domains.farming.models import Farmer
from core.constants import B2BRoleName


async def get_accessible_farmers_query(user_id: UUID, db: AsyncSession):
    """
    Get farmers accessible to user based on role hierarchy
    
    Hierarchy:
    - Owner/Admin: All farmers in tenant
    - Field Manager: Own farmers + team's farmers
    - Field Agent: Only own farmers
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        Query for accessible farmers
    """
    user = await db.get(UserModel, user_id)
    if not user:
        # Return empty query
        return select(Farmer).where(Farmer.id == None)
    
    # Get user's role
    if not user.role_id:
        # No role, only own farmers
        return select(Farmer).where(Farmer.created_by == user_id)
    
    role = await db.get(Role, user.role_id)
    if not role:
        return select(Farmer).where(Farmer.created_by == user_id)
    
    # Owner/Admin sees all farmers in tenant
    if role.name in (B2BRoleName.ADMIN, B2BRoleName.OWNER):
        return select(Farmer).where(Farmer.tenant_id == user.tenant_id)
    
    # All other roles see only their own farmers
    # (Field Manager team scope would need team implementation)
    return select(Farmer).where(Farmer.created_by == user_id)


async def can_access_farmer(user_id: UUID, farmer_id: UUID, db: AsyncSession) -> bool:
    """
    Check if user can access specific farmer
    
    Args:
        user_id: User ID
        farmer_id: Farmer ID
        db: Database session
        
    Returns:
        bool: True if user can access farmer
    """
    query = await get_accessible_farmers_query(user_id, db)
    query = query.where(Farmer.id == farmer_id)
    
    result = await db.execute(query)
    farmer = result.scalar_one_or_none()
    
    return farmer is not None
