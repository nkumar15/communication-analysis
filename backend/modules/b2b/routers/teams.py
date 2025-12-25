"""
Teams API Router - Manage teams and team membership
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from core.db.session import get_db
from modules.b2b.middleware import get_current_active_user
from modules.b2b.rbac import has_permission, can_manage_team, is_team_manager
from modules.b2b.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
    TeamMemberAdd,
    TeamMemberUpdate,
    TeamMemberResponse,
    MoveUserRequest,
    TeamStatsResponse
)
from modules.b2b.services import team_service
from modules.b2b.models import UserModel

router = APIRouter(prefix="/api/b2b/teams", tags=["teams"])


@router.get("/stats", response_model=TeamStatsResponse)
async def get_team_stats(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get team statistics for current user
    
    Returns team counts and user's team membership info.
    """
    stats = await team_service.get_team_stats(
        db, 
        current_user['tenant_id'], 
        current_user['id']
    )
    return TeamStatsResponse(**stats)


@router.get("/team-roles")
async def get_team_roles(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get available team role options
    
    Returns the list of valid team roles that can be assigned to team members.
    Uses team_role_definitions table for configurable roles.
    """
    from modules.b2b.services.team_role_service import team_role_service
    
    # Fetch team roles available to current tenant
    roles = await team_role_service.list_team_roles(
        db, 
        tenant_id=current_user.get('tenant_id'),
        include_system=True
    )
    
    # If no roles found, return hardcoded defaults as fallback
    if not roles:
        return [
            {"value": "team_manager", "label": "Team Manager"},
            {"value": "team_contributor", "label": "Contributor"},
            {"value": "team_reader", "label": "Reader"}
        ]
    
    return [
        {"value": r.name, "label": r.display_name}
        for r in roles
    ]


@router.get("/", response_model=List[TeamListResponse])
async def list_teams(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all teams for current tenant
    
    Requires: teams:read permission
    """
    # Check permission
    if not await has_permission(current_user['id'], 'teams', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view teams"
        )
    
    teams = await team_service.get_tenant_teams(db, current_user['tenant_id'])
    
    # Get member counts for each team
    response = []
    for team in teams:
        member_count = await team_service.get_team_member_count(db, team.id)
        response.append(TeamListResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            is_default=team.is_default,
            member_count=member_count,
            created_at=team.created_at
        ))
    
    return response


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team: TeamCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team
    
    Requires: teams:write permission
    Only owner/admin can create teams
    """
    # Check permission
    if not await has_permission(current_user['id'], 'teams', 'write', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create teams"
        )
    
    created_team = await team_service.create_team(
        db=db,
        tenant_id=current_user['tenant_id'],
        name=team.name,
        description=team.description,
        created_by=current_user['id'],
        config_data=team.config_data
    )
    
    await db.commit()
    
    member_count = await team_service.get_team_member_count(db, created_team.id)
    
    return TeamResponse(
        id=created_team.id,
        tenant_id=created_team.tenant_id,
        name=created_team.name,
        description=created_team.description,
        is_default=created_team.is_default,
        created_by=created_team.created_by,
        config_data=created_team.config_data,
        created_at=created_team.created_at,
        updated_at=created_team.updated_at,
        member_count=member_count
    )


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get team details
    
    Requires: teams:read permission
    """
    # Check permission
    if not await has_permission(current_user['id'], 'teams', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view teams"
        )
    
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify team belongs to user's tenant
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    member_count = await team_service.get_team_member_count(db, team.id)
    
    return TeamResponse(
        id=team.id,
        tenant_id=team.tenant_id,
        name=team.name,
        description=team.description,
        is_default=team.is_default,
        created_by=team.created_by,
        config_data=team.config_data,
        created_at=team.created_at,
        updated_at=team.updated_at,
        member_count=member_count
    )


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    updates: TeamUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update team details
    
    Requires: teams:write permission OR being a team_manager of this team
    """
    # Get team first to check tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user can manage this team
    if not await can_manage_team(current_user['id'], team_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this team"
        )
    
    updated_team = await team_service.update_team(
        db=db,
        team_id=team_id,
        name=updates.name,
        description=updates.description,
        config_data=updates.config_data
    )
    
    await db.commit()
    
    member_count = await team_service.get_team_member_count(db, updated_team.id)
    
    return TeamResponse(
        id=updated_team.id,
        tenant_id=updated_team.tenant_id,
        name=updated_team.name,
        description=updated_team.description,
        is_default=updated_team.is_default,
        created_by=updated_team.created_by,
        config_data=updated_team.config_data,
        created_at=updated_team.created_at,
        updated_at=updated_team.updated_at,
        member_count=member_count
    )


@router.delete("/{team_id}", status_code=status.HTTP_200_OK)
async def delete_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a team (soft delete)
    
    Requires: teams:delete permission
    Cannot delete the default team
    """
    # Check permission
    if not await has_permission(current_user['id'], 'teams', 'delete', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete teams"
        )
    
    # Get team to verify tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    await team_service.delete_team(db, team_id)
    await db.commit()
    return {"message": "Team deleted successfully"}


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    team_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List members of a team
    
    Requires: teams:read permission
    """
    # Check permission
    if not await has_permission(current_user['id'], 'teams', 'read', db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view teams"
        )
    
    # Verify team exists and belongs to tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    members = await team_service.get_team_members(db, team_id)
    
    return [
        TeamMemberResponse(
            id=member.id,
            team_id=member.team_id,
            user_id=member.user_id,
            team_role=member.team_role,
            user_email=user.email,
            user_name=user.name,
            joined_at=member.joined_at
        )
        for member, user in members
    ]


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: UUID,
    member: TeamMemberAdd,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a user to a team
    
    Requires: Being owner/admin OR team_manager of this team
    """
    # Verify team exists and belongs to tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user can manage this team
    if not await can_manage_team(current_user['id'], team_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this team"
        )
    
    # Verify the user being added belongs to same tenant
    user_to_add = await db.get(UserModel, member.user_id)
    if not user_to_add or user_to_add.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or belongs to different tenant"
        )
    
    team_member = await team_service.add_team_member(
        db=db,
        team_id=team_id,
        user_id=member.user_id,
        team_role=member.team_role
    )
    
    await db.commit()
    
    return TeamMemberResponse(
        id=team_member.id,
        team_id=team_member.team_id,
        user_id=team_member.user_id,
        team_role=team_member.team_role,
        user_email=user_to_add.email,
        user_name=user_to_add.name,
        joined_at=team_member.joined_at
    )


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a user from a team
    
    Requires: Being owner/admin OR team_manager of this team
    """
    # Verify team exists and belongs to tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user can manage this team
    if not await can_manage_team(current_user['id'], team_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this team"
        )
    
    # Check if target user is a team manager - only tenant admins can remove managers
    if await is_team_manager(user_id, team_id, db):
        if not await has_permission(current_user['id'], 'teams', 'write', db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only tenant admins can remove team managers"
            )
    
    await team_service.remove_team_member(db, team_id, user_id)
    await db.commit()
    return {"message": "Member removed successfully"}


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMemberResponse)
async def update_team_member_role(
    team_id: UUID,
    user_id: UUID,
    update: TeamMemberUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role in a team
    
    Requires: Being owner/admin OR team_manager of this team
    """
    # Verify team exists and belongs to tenant
    team = await team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user can manage this team
    if not await can_manage_team(current_user['id'], team_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this team"
        )
    
    team_member = await team_service.update_team_member_role(
        db=db,
        team_id=team_id,
        user_id=user_id,
        new_role=update.team_role
    )
    
    await db.commit()
    
    # Get user details
    user = await db.get(UserModel, user_id)
    
    return TeamMemberResponse(
        id=team_member.id,
        team_id=team_member.team_id,
        user_id=team_member.user_id,
        team_role=team_member.team_role,
        user_email=user.email if user else None,
        user_name=user.name if user else None,
        joined_at=team_member.joined_at
    )


@router.post("/members/{user_id}/move", status_code=status.HTTP_200_OK)
async def move_user_between_teams(
    user_id: UUID,
    move_request: MoveUserRequest,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Move a user from one team to another
    
    Requires: Being owner/admin OR team_manager of BOTH teams
    """
    # Verify both teams exist and belong to tenant
    from_team = await team_service.get_team_by_id(db, move_request.from_team_id)
    to_team = await team_service.get_team_by_id(db, move_request.to_team_id)
    
    if not from_team or not to_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both teams not found"
        )
    
    if from_team.tenant_id != current_user['tenant_id'] or to_team.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if user can manage both teams
    can_manage_from = await can_manage_team(current_user['id'], move_request.from_team_id, db)
    can_manage_to = await can_manage_team(current_user['id'], move_request.to_team_id, db)
    
    if not (can_manage_from and can_manage_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage one or both teams"
        )
    
    new_membership = await team_service.move_user_to_team(
        db=db,
        user_id=user_id,
        from_team_id=move_request.from_team_id,
        to_team_id=move_request.to_team_id,
        team_role=move_request.team_role
    )
    
    await db.commit()
    
    # Get user details
    user = await db.get(UserModel, user_id)
    
    return TeamMemberResponse(
        id=new_membership.id,
        team_id=new_membership.team_id,
        user_id=new_membership.user_id,
        team_role=new_membership.team_role,
        user_email=user.email if user else None,
        user_name=user.name if user else None,
        joined_at=new_membership.joined_at
    )


@router.get("/{team_id}/available-users")
async def get_available_users_for_team(
    team_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get users in tenant who are not already members of this team
    
    Returns list of users available to be added to the team.
    Requires: teams:write permission OR team_manager of this team
    """
    # Get available users via service
    available_users = await team_service.get_available_users_for_team(
        db, 
        current_user['tenant_id'], 
        team_id
    )
    
    return available_users
