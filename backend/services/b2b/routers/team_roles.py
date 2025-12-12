"""
Team Roles API Router

Endpoints for managing configurable team-level roles.
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.database import get_db
from services.b2b.middleware import get_current_active_user
from services.b2b.rbac import require_permission
from services.b2b.services.team_role_service import team_role_service


router = APIRouter(prefix="/api/b2b/team-roles", tags=["team-roles"])


# ============================================================================
# SCHEMAS
# ============================================================================

class TeamRoleResponse(BaseModel):
    """Team role response"""
    id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    can_manage_members: bool
    can_manage_settings: bool
    can_write_resources: bool
    can_delete_resources: bool
    is_system: bool
    is_default: bool
    
    class Config:
        from_attributes = True


class TeamRoleCreate(BaseModel):
    """Create team role request"""
    name: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z_]+$')
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    can_manage_members: bool = False
    can_manage_settings: bool = False
    can_write_resources: bool = True
    can_delete_resources: bool = False
    is_default: bool = False


class TeamRoleUpdate(BaseModel):
    """Update team role request"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    can_manage_members: Optional[bool] = None
    can_manage_settings: Optional[bool] = None
    can_write_resources: Optional[bool] = None
    can_delete_resources: Optional[bool] = None
    is_default: Optional[bool] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

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
        can_manage_members=data.can_manage_members,
        can_manage_settings=data.can_manage_settings,
        can_write_resources=data.can_write_resources,
        can_delete_resources=data.can_delete_resources,
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
