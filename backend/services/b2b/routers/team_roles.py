"""
Team Roles API Router

Endpoints for managing configurable team-level roles.
"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from services.b2b.rbac.decorators import require_permission
from services.b2b.services.team_role_service import team_role_service
from services.b2b.services.role_service import role_service  # For resources/actions
from services.b2b.schemas.team_roles import (
    TeamRoleCreate,
    TeamRoleUpdate,
    TeamRoleResponse
)
from services.b2b.schemas.roles import ResourceResponse
from services.b2b.schemas.actions_all import ActionsAllResponse


router = APIRouter(prefix="/api/b2b/team-roles", tags=["team-roles"])


@router.get("/resources", response_model=List[ResourceResponse])
async def list_resources(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List team-level resources only (excludes system resources).
    
    Used by frontend to build team role permission matrix.
    Only shows resources where is_system_resource = false.
    """
    from sqlalchemy import select, false
    from services.b2b.models.rbac import Resource
    
    stmt = select(Resource).where(
        Resource.is_system_resource == false()
    ).order_by(Resource.display_name)
    
    result = await db.execute(stmt)
    resources = result.scalars().all()
    
    return resources


@router.get("/actions", response_model=ActionsAllResponse)
async def list_actions(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all actions and team-level resources for permission matrix.
    
    Used by frontend to build permission selection UI.
    Only returns resources where is_system_resource = false.
    """
    from sqlalchemy import select, false
    from services.b2b.models.rbac import Resource
    
    # Get team-level resources only
    stmt = select(Resource).where(
        Resource.is_system_resource == false()
    ).order_by(Resource.display_name)
    
    result = await db.execute(stmt)
    resources = result.scalars().all()
    
    # Get all actions
    actions = await role_service.get_all_actions(db)
    
    return {
        "resources": resources,
        "actions": actions
    }



@router.get("", response_model=List[TeamRoleResponse])
async def list_team_roles(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all team roles available to current tenant.
    
    Returns system roles + tenant-specific custom roles.
    """
    tenant_id = current_user.get('tenant_id')
    roles = await team_role_service.list_team_roles(db, tenant_id=tenant_id)
    return roles


@router.get("/{role_id}", response_model=TeamRoleResponse)
async def get_team_role(
    role_id: UUID,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific team role by ID"""
    role = await team_role_service.get_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team role not found"
        )
    return role


@router.post("", response_model=TeamRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_team_role(
    data: TeamRoleCreate,
    current_user: dict = require_permission('teams', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a custom team role for current tenant.
    
    Requires teams:write permission.
    """
    tenant_id = current_user.get('tenant_id')
    
    # Check if role name already exists
    existing = await team_role_service.get_by_name(db, data.name, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Team role '{data.name}' already exists"
        )
    
    role = await team_role_service.create_role(
        db=db,
        tenant_id=tenant_id,
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        permissions=data.permissions,
        is_default=data.is_default
    )
    await db.commit()
    return role


@router.put("/{role_id}", response_model=TeamRoleResponse)
async def update_team_role(
    role_id: UUID,
    data: TeamRoleUpdate,
    current_user: dict = require_permission('teams', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a custom team role.
    
    System roles cannot be modified.
    Requires teams:write permission.
    """
    role = await team_role_service.get_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team role not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system roles"
        )
    
    # Only update provided fields
    update_data = data.model_dump(exclude_unset=True)
    role = await team_role_service.update_role(db, role, **update_data)
    await db.commit()
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_role(
    role_id: UUID,
    current_user: dict = require_permission('teams', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a custom team role.
    
    System roles cannot be deleted.
    Requires teams:delete permission.
    """
    role = await team_role_service.get_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team role not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system roles"
        )
    
    await team_role_service.delete_role(db, role)
    await db.commit()
