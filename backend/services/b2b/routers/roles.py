"""
Role Management API Router

Endpoints for viewing and managing roles and permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from core.database import get_db
from core.middleware import get_current_user
from services.b2b.rbac import require_permission
from services.b2b.models import Role, Resource, Action, RolePermission
from services.b2b.schemas.roles import (
    RoleResponse,
    RoleDetailResponse,
    ResourceResponse,
    ActionResponse,
    PermissionResponse,
    UpdateRolePermissionsRequest,
    CreateRoleRequest,
    RoleTemplateResponse
)
from services.b2b.services.role_template_service import role_template_service

router = APIRouter(prefix="/api/b2b/roles", tags=["roles"])


@router.get("/templates", response_model=list[RoleTemplateResponse])
async def list_templates(
    current_user: dict = require_permission('roles', 'read'),
    db: AsyncSession = Depends(get_db)
):
    """
    List all available role templates
    
    Permission required: roles:read
    """
    return await role_template_service.get_all_templates(db)


@router.post("", response_model=RoleResponse)
async def create_role(
    request: CreateRoleRequest,
    current_user: dict = require_permission('roles', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new role
    
    Permission required: roles:write
    """
    # Check if role with same name exists in tenant
    result = await db.execute(
        select(Role)
        .where(Role.tenant_id == current_user['tenant_id'])
        .where(Role.name == request.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )

    # Create role
    role = Role(
        tenant_id=current_user['tenant_id'],
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        is_system_role=False
    )
    db.add(role)
    await db.flush()

    # Apply template ONLY if explicit permissions are NOT provided
    # If permissions ARE provided, they are authoritative (UI sends full list including template perms)
    if request.template_id and not request.permissions:
        template = await role_template_service.get_template(db, request.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template ID"
            )
        await role_template_service.assign_permissions_from_template(db, role, template)
    
    # Apply custom permissions if provided
    # Use a set to track which permissions we're adding in this request
    added_in_request = set()
    
    if request.permissions:
        for perm in request.permissions:
            perm_key = (perm['resource_id'], perm['action_id'])
            
            # Skip if we've already added this permission in this request
            if perm_key in added_in_request:
                continue
            
            # Check if this permission already exists in DB (just in case)
            result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.resource_id == perm['resource_id'],
                    RolePermission.action_id == perm['action_id']
                )
            )
            existing = result.scalar_one_or_none()
            
            # Only add if it doesn't exist
            if not existing:
                role_perm = RolePermission(
                    role_id=role.id,
                    resource_id=perm['resource_id'],
                    action_id=perm['action_id']
                )
                db.add(role_perm)
                added_in_request.add(perm_key)
    
    await db.commit()
    await db.refresh(role)
    
    # Format permissions from the request for response (they were just created)
    permissions_list = []
    if request.permissions:
        for perm in request.permissions:
            # Find resource and action names from the IDs
            from uuid import UUID as UUIDType
            resource_uuid = UUIDType(perm['resource_id']) if isinstance(perm['resource_id'], str) else perm['resource_id']
            action_uuid = UUIDType(perm['action_id']) if isinstance(perm['action_id'], str) else perm['action_id']
            
            res_result = await db.execute(select(Resource).where(Resource.id == resource_uuid))
            resource = res_result.scalar_one_or_none()
            
            act_result = await db.execute(select(Action).where(Action.id == action_uuid))
            action = act_result.scalar_one_or_none()
            
            if resource and action:
                permissions_list.append({
                    "id": str(resource_uuid) + str(action_uuid),  # Dummy ID
                    "resource": resource.name,
                    "action": action.name
                })
    
    return {
        "id": str(role.id),
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "is_system_role": role.is_system_role,
        "is_active": role.is_active,
        "permissions": permissions_list
    }


@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID,
    current_user: dict = require_permission('roles', 'write'),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a role
    
    Permission required: roles:write
    """
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
    
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )

    # Check if any users are assigned to this role
    # We need to import UserModel here to avoid circular imports or use string reference if possible, 
    # but since we're in a router, we can import from models
    from services.b2b.models.user import UserModel
    
    user_count_result = await db.execute(
        select(func.count(UserModel.id))
        .where(UserModel.role_id == role_id)
        .where(UserModel.tenant_id == current_user['tenant_id'])
        .where(UserModel.deleted_at.is_(None))
    )
    user_count = user_count_result.scalar_one()
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role because it is assigned to {user_count} user(s)"
        )

    # Soft delete: set deleted_at timestamp
    role.deleted_at = func.now()
    await db.commit()
    
    return {"message": "Role deleted successfully"}


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
        .options(
            selectinload(Role.permissions)
            .selectinload(RolePermission.resource),
            selectinload(Role.permissions)
            .selectinload(RolePermission.action)
        )
        .where(Role.tenant_id == current_user['tenant_id'])
        .where(Role.is_active == True)
        .where(Role.deleted_at.is_(None))
        .order_by(Role.name)
    )
    roles = result.scalars().all()
    
    # Format response with permissions
    result_list = []
    for role in roles:
        permissions_list = []
        for perm in role.permissions:
            permissions_list.append({
                "id": str(perm.id),
                "resource": perm.resource.name,
                "action": perm.action.name
            })
        
        result_list.append({
            "id": str(role.id),
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "is_active": role.is_active,
            "permissions": permissions_list
        })
    
    return result_list


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
        .where(Role.deleted_at.is_(None))
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
