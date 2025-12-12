"""
Team Service - Business logic for team management
"""
from uuid import UUID
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from services.b2b.models import Team, TeamMember, UserModel
from services.b2b.models.team_role_definition import TeamRoleDefinition


async def create_team(
    db: AsyncSession,
    tenant_id: UUID,
    name: str,
    description: Optional[str] = None,
    created_by: Optional[UUID] = None,
    is_default: bool = False,
    config_data: Dict[str, Any] = None
) -> Team:
    """
    Create a new team
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        name: Team name
        description: Team description
        created_by: User ID who created the team
        is_default: Whether this is the default team
        config_data: Additional team configuration
        
    Returns:
        Created team
        
    Raises:
        HTTPException: If team name already exists in tenant
    """
    # Check if team name already exists
    existing = await db.execute(
        select(Team).where(
            Team.tenant_id == tenant_id,
            Team.name == name,
            Team.deleted_at.is_(None)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team with name '{name}' already exists"
        )
    
    team = Team(
        tenant_id=tenant_id,
        name=name,
        description=description,
        created_by=created_by,
        is_default=is_default,
        config_data=config_data or {}
    )
    
    db.add(team)
    await db.flush()
    # Re-query instead of refresh (RLS-compatible)
    result = await db.execute(select(Team).where(Team.id == team.id))
    team = result.scalar_one()
    
    # Add creator as team manager (if created_by is provided)
    if created_by:
        # Get or create team_manager role definition
        from services.b2b.models import TeamRoleDefinition
        role_def_result = await db.execute(
            select(TeamRoleDefinition).where(
                TeamRoleDefinition.name == "team_manager",
                (TeamRoleDefinition.tenant_id == tenant_id) | (TeamRoleDefinition.tenant_id.is_(None))
            ).order_by(TeamRoleDefinition.tenant_id.desc().nulls_last())
        )
        role_def = role_def_result.scalars().first()
        
        creator_member = TeamMember(
            team_id=team.id,
            user_id=created_by,
            team_role="team_manager",
            team_role_id=role_def.id if role_def else None
        )
        db.add(creator_member)
        await db.flush()
    
    return team


async def get_or_create_default_team(
    db: AsyncSession,
    tenant_id: UUID,
    created_by: Optional[UUID] = None
) -> Team:
    """
    Get the default team for a tenant, creating it if it doesn't exist
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        created_by: User ID (for creation only)
        
    Returns:
        Default team
    """
    # Try to find existing default team
    result = await db.execute(
        select(Team).where(
            Team.tenant_id == tenant_id,
            Team.is_default == True,
            Team.deleted_at.is_(None)
        )
    )
    default_team = result.scalar_one_or_none()
    
    if not default_team:
        # Create default team
        default_team = await create_team(
            db=db,
            tenant_id=tenant_id,
            name="Default Team",
            description="Default team for all users",
            created_by=created_by,
            is_default=True
        )
    
    return default_team


async def get_tenant_teams(
    db: AsyncSession,
    tenant_id: UUID,
    include_deleted: bool = False
) -> List[Team]:
    """Get all teams for a tenant"""
    query = select(Team).where(Team.tenant_id == tenant_id)
    
    if not include_deleted:
        query = query.where(Team.deleted_at.is_(None))
    
    query = query.order_by(Team.is_default.desc(), Team.created_at.desc())
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_team_by_id(db: AsyncSession, team_id: UUID) -> Optional[Team]:
    """Get team by ID"""
    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def update_team(
    db: AsyncSession,
    team_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    config_data: Optional[Dict[str, Any]] = None
) -> Team:
    """
    Update team details
    
    Args:
        db: Database session
        team_id: Team ID
        name: New name (optional)
        description: New description (optional)
        config_data: New config_data (optional)
        
    Returns:
        Updated team
        
    Raises:
        HTTPException: If team not found or name conflict
    """
    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check name uniqueness if changing name
    if name and name != team.name:
        existing = await db.execute(
            select(Team).where(
                Team.tenant_id == team.tenant_id,
                Team.name == name,
                Team.id != team_id,
                Team.deleted_at.is_(None)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team with name '{name}' already exists"
            )
        team.name = name
    
    if description is not None:
        team.description = description
    
    if config_data is not None:
        team.config_data = config_data
    
    await db.flush()
    # Re-query instead of refresh (RLS-compatible)
    result = await db.execute(select(Team).where(Team.id == team.id))
    team = result.scalar_one()
    
    return team


async def delete_team(db: AsyncSession, team_id: UUID) -> None:
    """
    Soft delete a team
    
    Args:
        db: Database session
        team_id: Team ID
        
    Raises:
        HTTPException: If team not found or is default team
    """
    from datetime import datetime, timezone
    
    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default team"
        )
    
    team.deleted_at = datetime.now(timezone.utc)
    await db.flush()


async def get_team_members(
    db: AsyncSession,
    team_id: UUID
) -> List[tuple[TeamMember, UserModel]]:
    """
    Get all members of a team with their user details
    
    Returns:
        List of (TeamMember, UserModel) tuples
    """
    result = await db.execute(
        select(TeamMember, UserModel)
        .join(UserModel, TeamMember.user_id == UserModel.id)
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.team_role, UserModel.email)
    )
    return list(result.all())


async def get_team_member_count(db: AsyncSession, team_id: UUID) -> int:
    """Get count of members in a team"""
    result = await db.execute(
        select(func.count(TeamMember.id)).where(TeamMember.team_id == team_id)
    )
    return result.scalar() or 0


async def add_team_member(
    db: AsyncSession,
    team_id: UUID,
    user_id: UUID,
    team_role: str = "team_contributor"
) -> TeamMember:
    """
    Add a user to a team
    
    Args:
        db: Database session
        team_id: Team ID
        user_id: User ID
        team_role: Role within the team
        
    Returns:
        Created team member
        
    Raises:
        HTTPException: If team/user not found or user already in team
    """
    # Verify team exists
    team = await get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify user exists
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already a member
    existing = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team"
        )
    
    # Look up team_role_id from team_role_definitions
    # First try to find by name, checking both system roles and tenant-specific roles
    team = await get_team_by_id(db, team_id)
    role_def_result = await db.execute(
        select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == team_role,
            (TeamRoleDefinition.tenant_id.is_(None)) | (TeamRoleDefinition.tenant_id == team.tenant_id)
        ).order_by(TeamRoleDefinition.tenant_id.desc().nulls_last())  # Prefer tenant-specific
    )
    role_def = role_def_result.scalars().first()
    
    member = TeamMember(
        team_id=team_id,
        user_id=user_id,
        team_role=team_role,
        team_role_id=role_def.id if role_def else None
    )
    
    db.add(member)
    await db.flush()
    # Re-query instead of refresh (RLS-compatible)
    result = await db.execute(select(TeamMember).where(TeamMember.id == member.id))
    member = result.scalar_one()
    
    return member


async def remove_team_member(
    db: AsyncSession,
    team_id: UUID,
    user_id: UUID
) -> None:
    """
    Remove a user from a team
    
    Args:
        db: Database session
        team_id: Team ID
        user_id: User ID
        
    Raises:
        HTTPException: If membership not found
    """
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this team"
        )
    
    await db.delete(member)
    await db.flush()


async def update_team_member_role(
    db: AsyncSession,
    team_id: UUID,
    user_id: UUID,
    new_role: str
) -> TeamMember:
    """
    Update a user's role in a team
    
    Args:
        db: Database session
        team_id: Team ID
        user_id: User ID
        new_role: New team role
        
    Returns:
        Updated team member
        
    Raises:
        HTTPException: If membership not found
    """
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this team"
        )
    
    # Look up new role definition
    # Check tenant-specific first, then system
    team = await get_team_by_id(db, team_id)
    role_def_result = await db.execute(
        select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == new_role,
            (TeamRoleDefinition.tenant_id.is_(None)) | (TeamRoleDefinition.tenant_id == team.tenant_id)
        ).order_by(TeamRoleDefinition.tenant_id.desc().nulls_last())
    )
    role_def = role_def_result.scalars().first()
    
    member.team_role = new_role
    member.team_role_id = role_def.id if role_def else None
    
    await db.flush()
    # Re-query instead of refresh (Standardization)
    result = await db.execute(select(TeamMember).where(TeamMember.id == member.id))
    member = result.scalar_one()
    
    return member


async def get_user_teams(db: AsyncSession, user_id: UUID) -> List[tuple[Team, TeamMember]]:
    """
    Get all teams a user belongs to
    
    Returns:
        List of (Team, TeamMember) tuples
    """
    result = await db.execute(
        select(Team, TeamMember)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(
            TeamMember.user_id == user_id,
            Team.deleted_at.is_(None)
        )
        .order_by(Team.is_default.desc(), Team.name)
    )
    return list(result.all())


async def move_user_to_team(
    db: AsyncSession,
    user_id: UUID,
    from_team_id: UUID,
    to_team_id: UUID,
    team_role: str = "team_contributor"
) -> TeamMember:
    """
    Move a user from one team to another
    
    Args:
        db: Database session
        user_id: User ID
        from_team_id: Source team ID
        to_team_id: Destination team ID
        team_role: Role in the new team
        
    Returns:
        New team membership
    """
    # Remove from old team
    await remove_team_member(db, from_team_id, user_id)
    
    # Add to new team
    return await add_team_member(db, to_team_id, user_id, team_role)
