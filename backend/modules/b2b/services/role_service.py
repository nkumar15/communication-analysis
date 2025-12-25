"""
Role Service

Manages tenant-specific roles and their permissions.
Encapsulates business logic for role creation, updates, and binding.
"""
from uuid import UUID
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from modules.b2b.models import Role, RolePermission, Resource, Action
from modules.b2b.schemas.roles import RoleCreate, RoleUpdate


class RoleService:
    async def get_all_roles(self, db: AsyncSession, tenant_id: UUID) -> List[Role]:
        """List all roles for a tenant"""
        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.permissions).joinedload(RolePermission.resource),
                selectinload(Role.permissions).joinedload(RolePermission.action)
            )
            .where(
                Role.tenant_id == tenant_id,
                Role.deleted_at.is_(None)
            )
        )
        return result.scalars().all()

    async def get_role_by_id(self, db: AsyncSession, role_id: UUID) -> Optional[Role]:
        """Get role by ID (tenant-agnostic fetch, verify tenant in router if needed)"""
        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.permissions).joinedload(RolePermission.resource),
                selectinload(Role.permissions).joinedload(RolePermission.action)
            )
            .where(Role.id == role_id)
        )
        return result.scalars().first()

    async def get_role_by_name(self, db: AsyncSession, name: str, tenant_id: UUID) -> Optional[Role]:
        """Get role by name for a tenant"""
        result = await db.execute(
            select(Role).where(
                Role.name == name,
                Role.tenant_id == tenant_id,
                Role.deleted_at.is_(None)
            )
        )
        return result.scalars().first()

    async def create_role(
        self, 
        db: AsyncSession, 
        tenant_id: UUID, 
        role_data: RoleCreate
    ) -> Role:
        """Create a new role with permissions"""
        # Check duplicate name
        existing = await self.get_role_by_name(db, role_data.name, tenant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role '{role_data.name}' already exists"
            )

        # Create role
        role = Role(
            tenant_id=tenant_id,
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            is_system_role=False  # Custom roles are never system roles
        )
        db.add(role)
        await db.flush()  # Get ID

        # Apply template permissions if template_id provided and no explicit permissions
        if role_data.template_id and not role_data.permissions:
            from modules.b2b.services.role_template_service import role_template_service
            template = await role_template_service.get_template(db, role_data.template_id)
            if template:
                await role_template_service.assign_permissions_from_template(db, role, template)

        # Add explicit permissions if provided
        if role_data.permissions:
            await self._update_permissions(db, role.id, role_data.permissions)

        # Re-fetch with eager loading for proper serialization
        await db.flush()
        return await self.get_role_by_id(db, role.id)

    async def update_role(
        self, 
        db: AsyncSession, 
        role: Role, 
        update_data: RoleUpdate
    ) -> Role:
        """Update role details and permissions"""
        if role.is_system_role:
             # Prevent updating core fields of system roles, but allow permission tweaks if design allows
             # For now, we block system role updates entirely at service level to be safe
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles"
            )

        # Update fields
        if update_data.display_name is not None:
            role.display_name = update_data.display_name
        if update_data.description is not None:
            role.description = update_data.description
        
        # Update permissions if provided
        if update_data.permissions is not None:
            # Clear existing logic
            await db.execute(
                delete(RolePermission).where(RolePermission.role_id == role.id)
            )
            await self._update_permissions(db, role.id, update_data.permissions)

        # Re-fetch with eager loading for proper serialization
        await db.flush()
        return await self.get_role_by_id(db, role.id)

    async def delete_role(self, db: AsyncSession, role: Role) -> None:
        """Soft delete a role"""
        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete system roles"
            )
            
        # Optional: Check if users are assigned to this role before deleting
        # This implementation assumes generic soft-delete allows it
        
        role.deleted_at = func.now()
        # db.commit() is handled by caller/dependency

    async def _update_permissions(
        self, 
        db: AsyncSession, 
        role_id: UUID, 
        permissions: List[Dict]
    ):
        """
        Helper to batch insert permissions.
        
        Permissions format: [{"resource_id": "uuid", "action_id": "uuid"}, ...]
        """
        for perm in permissions:
            resource_id = perm.get('resource_id')
            action_id = perm.get('action_id')
            
            if not resource_id or not action_id:
                continue  # Skip malformed permissions
                
            db.add(RolePermission(
                role_id=role_id,
                resource_id=resource_id,
                action_id=action_id
            ))

    async def get_all_resources(self, db: AsyncSession) -> List[Resource]:
        """List all available resources"""
        result = await db.execute(select(Resource))
        return result.scalars().all()

    async def get_all_actions(self, db: AsyncSession) -> List[Action]:
        """List all available actions"""
        result = await db.execute(select(Action))
        return result.scalars().all()

# Singleton instance
role_service = RoleService()
