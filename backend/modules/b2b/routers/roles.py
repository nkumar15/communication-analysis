"""
Role Management API Router

Handles CRUD operations for tenant roles and permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from core.db.session import get_db
from modules.b2b.middleware import get_current_active_user
from modules.b2b.rbac.decorators import require_permission
from modules.b2b.schemas.roles import RoleCreate, RoleUpdate, RoleResponse, RoleTemplateResponse, ResourceResponse
from modules.b2b.schemas.actions_all import ActionsAllResponse
from modules.b2b.services.role_service import role_service
from modules.b2b.services.role_template_service import role_template_service


router = APIRouter(prefix="/api/b2b/roles", tags=["roles"])


@router.get("/templates", response_model=List[RoleTemplateResponse])
async def list_templates(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available role templates
    
    Permission required: roles:read
    """
    return await role_template_service.get_all_templates(db)



@router.get("/actions/all", response_model=ActionsAllResponse)
async def list_actions_and_resources(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available actions and resources for defining permissions
    
    Permission required: roles:read
    """
    resources = await role_service.get_all_resources(db)
    actions = await role_service.get_all_actions(db)
    return {
        "resources": resources,
        "actions": actions
    }


@router.get("/resources/all", response_model=List[ResourceResponse])
async def list_resources(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available resources
    
    Permission required: roles:read
    """
    return await role_service.get_all_resources(db)


@router.post("", response_model=RoleResponse)
async def create_role(
    request: RoleCreate,
    current_user: dict = require_permission('roles', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new tenant role
    
    Permission required: roles:write
    """
    role = await role_service.create_role(
        db, 
        current_user['tenant_id'], 
        request
    )
    await db.commit()
    return role


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all roles for the current tenant
    
    Permission required: roles:read
    """
    return await role_service.get_all_roles(db, current_user['tenant_id'])


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific role
    
    Permission required: roles:read
    """
    role = await role_service.get_role_by_id(db, role_id)
    if not role or role.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    request: RoleUpdate,
    current_user: dict = require_permission('roles', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a role's details or permissions
    
    Permission required: roles:write
    """
    # Verify ownership
    role = await role_service.get_role_by_id(db, role_id)
    if not role or role.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    updated_role = await role_service.update_role(db, role, request)
    await db.commit()
    return updated_role


@router.delete("/{role_id}", status_code=status.HTTP_200_OK)
async def delete_role(
    role_id: UUID,
    current_user: dict = require_permission('roles', 'delete'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a role
    
    Permission required: roles:delete
    """
    role = await role_service.get_role_by_id(db, role_id)
    if not role or role.tenant_id != current_user['tenant_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    await role_service.delete_role(db, role)
    await db.commit()
    return {"message": "Role deleted successfully"}
