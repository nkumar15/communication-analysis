from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from modules.b2b.models.rbac import Role, Resource, Action, RolePermission
from modules.b2b.models.role_template import RoleTemplate
from uuid import UUID

class RoleTemplateService:
    """
    Service to manage role templates and seeding for tenants.
    Fetches templates from b2b.role_templates table.
    """

    async def seed_tenant_roles(self, db: AsyncSession, tenant_id: UUID) -> None:
        """
        Seeds default roles and permissions for a new tenant based on templates.
        """
        # 1. Fetch all Resources and Actions to map names to IDs
        resources = await self._get_resource_map(db)
        actions = await self._get_action_map(db)

        # 2. Fetch default templates from DB
        templates = await self._get_default_templates(db)

        for template in templates:
            # 3. Create Role
            role = await self._create_role(db, tenant_id, template)
            
            # 4. Assign Permissions
            await self._assign_permissions(db, role, template.permissions, resources, actions)

    async def get_all_templates(self, db: AsyncSession) -> List[RoleTemplate]:
        """
        Get all available role templates
        """
        result = await db.execute(select(RoleTemplate))
        return result.scalars().all()

    async def get_template(self, db: AsyncSession, template_id: UUID) -> RoleTemplate:
        """
        Get a specific template by ID
        """
        result = await db.execute(
            select(RoleTemplate).where(RoleTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def assign_permissions_from_template(self, db: AsyncSession, role: Role, template: RoleTemplate) -> None:
        """
        Assign permissions to a role based on a template
        """
        resources = await self._get_resource_map(db)
        actions = await self._get_action_map(db)
        await self._assign_permissions(db, role, template.permissions, resources, actions)

    async def _get_default_templates(self, db: AsyncSession) -> List[RoleTemplate]:
        result = await db.execute(
            select(RoleTemplate).where(RoleTemplate.is_default == True)
        )
        return result.scalars().all()

    async def _get_resource_map(self, db: AsyncSession) -> Dict[str, UUID]:
        result = await db.execute(select(Resource))
        return {r.name: r.id for r in result.scalars().all()}

    async def _get_action_map(self, db: AsyncSession) -> Dict[str, UUID]:
        result = await db.execute(select(Action))
        return {a.name: a.id for a in result.scalars().all()}

    async def _create_role(self, db: AsyncSession, tenant_id: UUID, template: RoleTemplate) -> Role:
        # Check if role exists
        result = await db.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.name == template.name
            )
        )
        role = result.scalar_one_or_none()

        if not role:
            role = Role(
                tenant_id=tenant_id,
                name=template.name,
                display_name=template.display_name,
                description=template.description,
                is_system_role=template.is_system_role
            )
            db.add(role)
            await db.flush() # Flush to get ID
        
        return role

    async def _assign_permissions(
        self, 
        db: AsyncSession, 
        role: Role, 
        perms_def: List[Dict[str, Any]], 
        resource_map: Dict[str, UUID], 
        action_map: Dict[str, UUID]
    ) -> None:
        
        for perm in perms_def:
            resource_name = perm["resource"]
            action_names = perm["actions"]
            
            if resource_name not in resource_map:
                continue # Skip if resource doesn't exist (e.g. feature flag off)

            resource_id = resource_map[resource_name]

            for action_name in action_names:
                if action_name not in action_map:
                    continue

                action_id = action_map[action_name]

                # Check if permission exists
                result = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.resource_id == resource_id,
                        RolePermission.action_id == action_id
                    )
                )
                existing_perm = result.scalar_one_or_none()

                if not existing_perm:
                    new_perm = RolePermission(
                        role_id=role.id,
                        resource_id=resource_id,
                        action_id=action_id
                    )
                    db.add(new_perm)

# Singleton instance
role_template_service = RoleTemplateService()
