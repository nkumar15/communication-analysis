"""
Scope Helpers - Hierarchical Data Access

Determines what data a user can access based on reporting structure.
"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models import UserModel
from app.rbac_models import Role, Farmer


async def get_accessible_user_ids(user_id: int, db: AsyncSession) -> list[int]:
    """
    Get all user IDs that are accessible to this user based on hierarchy
    
    Hierarchy:
    - Admin: All users in tenant
    - Field Manager: Self + users they invited (field agents)
    - Field Agent: Only self
    
    Args:
        user_id: User ID to check
        db: Database session
        
    Returns:
        list[int]: List of accessible user IDs
    """
    user = await db.get(UserModel, user_id)
    if not user:
        return []
    
    # Get user's role
    if not user.role_id:
        return [user_id]  # Only self if no role
    
    role = await db.get(Role, user.role_id)
    if not role:
        return [user_id]
    
    # Admin sees all users in tenant
    if role.name == 'admin':
        result = await db.execute(
            select(UserModel.id).where(UserModel.tenant_id == user.tenant_id)
        )
        return [row[0] for row in result]
    
    # Field Manager sees self + users they invited
    if role.name == 'field_manager':
        result = await db.execute(
            select(UserModel.id).where(
                or_(
                    UserModel.id == user_id,
                    UserModel.invited_by == user_id
                )
            )
        )
        return [row[0] for row in result]
    
    # Field Agent sees only self
    return [user_id]


async def get_accessible_farmers_query(user_id: int, db: AsyncSession):
    """
    Get SQLAlchemy query for farmers accessible to this user
    
    Scope:
    - Admin: All farmers in tenant
    - Field Manager: Farmers created by self + team (invited users)
    - Field Agent: Only farmers they created
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        select: SQLAlchemy select statement for accessible farmers
    """
    user = await db.get(UserModel, user_id)
    if not user:
        # Return empty query
        return select(Farmer).where(Farmer.id == -1)
    
    # Get user's role
    if not user.role_id:
        # No role - only see own farmers
        return select(Farmer).where(Farmer.created_by == user_id)
    
    role = await db.get(Role, user.role_id)
    if not role:
        return select(Farmer).where(Farmer.created_by == user_id)
    
    # Admin sees all farmers in tenant
    if role.name == 'admin':
        return select(Farmer).where(Farmer.tenant_id == user.tenant_id)
    
    # Field Manager sees farmers created by team
    if role.name == 'field_manager':
        team_ids = await get_accessible_user_ids(user_id, db)
        return select(Farmer).where(Farmer.created_by.in_(team_ids))
    
    # Field Agent sees only their own farmers
    return select(Farmer).where(Farmer.created_by == user_id)


async def can_access_farmer(user_id: int, farmer_id: int, db: AsyncSession) -> bool:
    """
    Check if user can access a specific farmer
    
    Args:
        user_id: User ID
        farmer_id: Farmer ID to check
        db: Database session
        
    Returns:
        bool: True if user can access this farmer
    """
    query = await get_accessible_farmers_query(user_id, db)
    result = await db.execute(query.where(Farmer.id == farmer_id))
    farmer = result.scalar_one_or_none()
    return farmer is not None


async def can_access_user(current_user_id: int, target_user_id: int, db: AsyncSession) -> bool:
    """
    Check if current user can access target user's data
    
    Args:
        current_user_id: User performing the action
        target_user_id: User whose data is being accessed
        db: Database session
        
    Returns:
        bool: True if current user can access target user
    """
    accessible_ids = await get_accessible_user_ids(current_user_id, db)
    return target_user_id in accessible_ids


async def get_dashboard_stats(user_id: int, db: AsyncSession) -> dict:
    """
    Get dashboard statistics scoped to user's access level
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        dict: Statistics scoped to user
    """
    from sqlalchemy import func, and_
    
    user = await db.get(UserModel, user_id)
    if not user:
        return {
            "total_users": 0,
            "total_farmers": 0,
            "my_farmers": 0
        }
    
    # Get accessible user IDs
    accessible_user_ids = await get_accessible_user_ids(user_id, db)
    
    # Count accessible users
    user_count_result = await db.execute(
        select(func.count(UserModel.id)).where(
            UserModel.id.in_(accessible_user_ids)
        )
    )
    total_users = user_count_result.scalar()
    
    # Count accessible farmers
    farmers_query = await get_accessible_farmers_query(user_id, db)
    farmer_count_result = await db.execute(
        select(func.count()).select_from(farmers_query.subquery())
    )
    total_farmers = farmer_count_result.scalar()
    
    # Count user's own farmers
    my_farmers_result = await db.execute(
        select(func.count(Farmer.id)).where(Farmer.created_by == user_id)
    )
    my_farmers = my_farmers_result.scalar()
    
    return {
        "total_users": total_users,
        "total_farmers": total_farmers,
        "my_farmers": my_farmers,
        "accessible_users": len(accessible_user_ids)
    }
