"""
Role Management API Router

Endpoints for viewing and managing roles and permissions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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

    # Apply template if provided
    if request.template_id:
        template = await role_template_service.get_template(db, request.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template ID"
            )
        await role_template_service.assign_permissions_from_template(db, role, template)
    
    # Apply custom permissions if provided (overrides template if both present, or adds to it)
    if request.permissions:
        # If template was used, we might want to clear existing permissions first if the intent is "replace"
        # But for now let's assume "append/overwrite" logic or just "use provided list"
        
        # If we want to strictly follow "manual selection overrides template", we should probably
        # just use the manual list if provided.
        
        # Let's support:
        # 1. Template only -> use template perms
        # 2. Permissions only -> use provided perms
        # 3. Both -> Apply template, then add/overwrite with provided perms (or maybe just use provided perms if the UI sends the full set)
        
        # UI logic will likely be: User selects template -> UI pre-fills checkboxes -> User modifies -> UI sends FULL list of permissions.
        # So if permissions are sent, we should probably rely on them.
        
        # However, to be safe and support "template + extra", let's just add them.
        # But wait, if the UI sends the FULL list, we should probably clear any template-added ones first to avoid duplicates or stale ones?
        # Actually, if the UI sends the full list, we should probably NOT apply the template logic in backend, OR clear it.
        
        # Better approach: If `permissions` is provided, use ONLY that. If not, use `template_id`.
        # But the request model allows both.
        
        # Let's stick to: If `permissions` is provided, use it. If `template_id` is provided AND `permissions` is empty/None, use template.
        pass

    if request.permissions:
        # If permissions are explicitly provided, we use them (and they might have been pre-filled from template in UI)
        # So we don't need to call assign_permissions_from_template if permissions are present.
        # BUT, if we want to support "create from template" API call without sending full perms list, we need the template logic.
        
        # Refined Logic:
        # 1. If template_id provided, apply template permissions.
        # 2. If permissions provided, apply them (upsert/add).
        # This allows "Template + Extra" or "Just Template" or "Just Custom".
        # If UI sends full list, it shouldn't send template_id if it wants full control, OR it sends template_id just for reference?
        # Let's assume UI sends full list if modified.
        
        for perm in request.permissions:
            # Check if exists (if template already added it)
            result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.resource_id == perm['resource_id'],
                    RolePermission.action_id == perm['action_id']
                )
            )
            if not result.scalar_one_or_none():
                role_perm = RolePermission(
                    role_id=role.id,
                    resource_id=perm['resource_id'],
                    action_id=perm['action_id']
                )
                db.add(role_perm)
    
    await db.commit()
    await db.refresh(role)
    return role


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

    # Delete permissions first (cascade should handle this but being explicit is safer)
    await db.execute(
        RolePermission.__table__.delete().where(RolePermission.role_id == role_id)
    )
    
    await db.delete(role)
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
