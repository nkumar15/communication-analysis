"""
Role Management API Router

Endpoints for viewing and managing roles and permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.middleware.auth import get_current_user
from app.rbac import require_permission
from app.rbac_models import Role, Resource, Action, RolePermission
from app.schemas.roles import (
    RoleResponse,
    RoleDetailResponse,
    ResourceResponse,
    ActionResponse,
    PermissionResponse,
    UpdateRolePermissionsRequest
)

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all roles for the current tenant
    
    Permission required: roles:read
    """
    result = await db.execute(
        select(Role)
        .where(Role.tenant_id == current_user['tenant_id'])
        .where(Role.is_active == True)
        .order_by(Role.name)
    )
    roles = result.scalars().all()
    return roles


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role_details(
    role_id: UUID,
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get role details with permissions
    
    Permission required: roles:read
    """
    result = await db.execute(
        select(Role)
        .options(
            selectinload(Role.permissions)
            .selectinload(RolePermission.resource),
            selectinload(Role.permissions)
            .selectinload(RolePermission.action)
        )
        .where(Role.id == role_id)
        .where(Role.tenant_id == current_user['tenant_id'])
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Format permissions for response
    permissions = []
    for perm in role.permissions:
        permissions.append(PermissionResponse(
            resource=ResourceResponse.from_orm(perm.resource),
            action=ActionResponse.from_orm(perm.action)
        ))
    
    return RoleDetailResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
        permissions=permissions
    )


@router.put("/{role_id}/permissions")
async def update_role_permissions(
    role_id: UUID,
    request: UpdateRolePermissionsRequest,
    current_user: dict = require_permission('roles', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update permissions for a role
    
    Permission required: roles:write
    
    This replaces all existing permissions with the new set.
    """
    # Get role
    result = await db.execute(
        select(Role)
        .where(Role.id == role_id)
        .where(Role.tenant_id == current_user['tenant_id'])
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Delete existing permissions
    await db.execute(
        RolePermission.__table__.delete().where(RolePermission.role_id == role_id)
    )
    
    # Add new permissions
    for perm in request.permissions:
        role_perm = RolePermission(
            role_id=role_id,
            resource_id=perm['resource_id'],
            action_id=perm['action_id']
        )
        db.add(role_perm)
    
    await db.commit()
    
    return {"message": "Permissions updated successfully"}


@router.get("/resources/all", response_model=list[ResourceResponse])
async def list_resources(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available resources
    
    Permission required: roles:read
    """
    result = await db.execute(
        select(Resource).order_by(Resource.category, Resource.name)
    )
    resources = result.scalars().all()
    return resources


@router.get("/actions/all", response_model=list[ActionResponse])
async def list_actions(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available actions
    
    Permission required: roles:read
    """
    result = await db.execute(
        select(Action).order_by(Action.name)
    )
    actions = result.scalars().all()
    return actions
