"""
Scope Helpers - Hierarchical Data Access

Determines what data a user can access based on roles and team membership.
This is the B2B boilerplate - domain-specific logic should be in domain modules.
"""
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from services.b2b.models import UserModel, Role, Team, TeamMember
from core.constants import B2BRoleName


async def get_accessible_user_ids(user_id: UUID, db: AsyncSession) -> list[UUID]:
    """
    Get all user IDs that are accessible to this user based on role
    
    Hierarchy:
    - Owner/Admin: All users in tenant
    - Others: All users in tenant
    
    Args:
        user_id: User ID to check
        db: Database session
        
    Returns:
        list[UUID]: List of accessible user IDs
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
    
    # Owner/Admin sees all users in tenant
    if role.name in (B2BRoleName.ADMIN, B2BRoleName.OWNER):
        result = await db.execute(
            select(UserModel.id).where(UserModel.tenant_id == user.tenant_id)
        )
        return [row[0] for row in result]
    
    # Viewers only see themselves
    if role.name == B2BRoleName.VIEWER:
        return [user_id]
    
    # Other roles (field_manager, etc.) see all users in tenant
    result = await db.execute(
        select(UserModel.id).where(UserModel.tenant_id == user.tenant_id)
    )
    return [row[0] for row in result]


async def can_access_user(current_user_id: UUID, target_user_id: UUID, db: AsyncSession) -> bool:
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


# ============================================================================
# Team-Related Functions
# ============================================================================

async def get_user_team_ids(user_id: UUID, db: AsyncSession) -> list[UUID]:
    """
    Get IDs of teams user belongs to
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        list[UUID]: List of team IDs
    """
    result = await db.execute(
        select(TeamMember.team_id).where(TeamMember.user_id == user_id)
    )
    return [row[0] for row in result]


async def is_team_manager(user_id: UUID, team_id: UUID, db: AsyncSession) -> bool:
    """
    Check if user is a team manager for given team
    
    Args:
        user_id: User ID
        team_id: Team ID
        db: Database session
        
    Returns:
        bool: True if user is team manager
    """
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == user_id,
            TeamMember.team_id == team_id,
            TeamMember.team_role == 'team_manager'
        )
    )
    return result.scalar_one_or_none() is not None


async def can_manage_team(user_id: UUID, team_id: UUID, db: AsyncSession) -> bool:
    """
    Check if user can manage team (owner/admin or team_manager)
    
    Args:
        user_id: User ID
        team_id: Team ID
        db: Database session
        
    Returns:
        bool: True if user can manage the team
    """
    user = await db.get(UserModel, user_id)
    if not user or not user.role_id:
        return False
    
    role = await db.get(Role, user.role_id)
    
    # System admins can manage all teams
    if role and role.name in (B2BRoleName.OWNER, B2BRoleName.ADMIN):
        return True
    
    # Check if user is team manager
    return await is_team_manager(user_id, team_id, db)


async def get_team_user_ids(team_id: UUID, db: AsyncSession) -> list[UUID]:
    """
    Get all user IDs that are members of a team
    
    Args:
        team_id: Team ID
        db: Database session
        
    Returns:
        list[UUID]: List of user IDs in the team
    """
    result = await db.execute(
        select(TeamMember.user_id).where(TeamMember.team_id == team_id)
    )
    return [row[0] for row in result]


# ============================================================================
# Dashboard Statistics
# ============================================================================

async def get_dashboard_stats(user_id: UUID, db: AsyncSession, team_id: UUID = None) -> dict:
    """
    Get dashboard statistics scoped to user's access level
    
    Optionally filter by team for team-specific dashboards.
    
    Args:
        user_id: User ID
        db: Database session
        team_id: Optional team ID to filter stats by team
        
    Returns:
        dict: Statistics including user counts and team info
    """
    user = await db.get(UserModel, user_id)
    if not user:
        return {
            "total_users": 0,
            "accessible_users": 0,
            "total_teams": 0,
            "user_teams_count": 0
        }
    
    # Get accessible user IDs
    accessible_user_ids = await get_accessible_user_ids(user_id, db)
    
    # Count accessible users
    user_count_result = await db.execute(
        select(func.count(UserModel.id)).where(
            UserModel.id.in_(accessible_user_ids)
        )
    )
    total_users = user_count_result.scalar() or 0
    
    # If team_id provided, filter by team members
    team_users_count = total_users
    if team_id:
        team_member_ids = await get_team_user_ids(team_id, db)
        # Intersection of accessible users and team members
        team_accessible_ids = [uid for uid in accessible_user_ids if uid in team_member_ids]
        team_users_count = len(team_accessible_ids)
    
    # Count teams in tenant
    teams_count_result = await db.execute(
        select(func.count(Team.id)).where(
            Team.tenant_id == user.tenant_id,
            Team.deleted_at.is_(None)
        )
    )
    total_teams = teams_count_result.scalar() or 0
    
    # Count user's teams
    user_teams = await get_user_team_ids(user_id, db)
    
    return {
        "total_users": total_users,
        "accessible_users": total_users if not team_id else team_users_count,
        "total_teams": total_teams,
        "user_teams_count": len(user_teams),
        "team_id": team_id  # Echo back for context
    }
