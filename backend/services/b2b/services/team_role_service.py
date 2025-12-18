"""
Team Role Definition Service

CRUD operations for configurable team-level roles.
"""
from uuid import UUID
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from services.b2b.models.team_role_definition import TeamRoleDefinition


class TeamRoleService:
    """Service for team role definition operations"""
    
    async def list_team_roles(
        self, 
        db: AsyncSession, 
        tenant_id: Optional[UUID] = None,
        include_system: bool = True
    ) -> List[TeamRoleDefinition]:
        """
        List team roles available to a tenant.
        
        Args:
            db: Database session (with RLS context set)
            tenant_id: Optional tenant ID to filter custom roles
            include_system: Whether to include system roles (default True)
            
        Returns:
            List of team role definitions ordered by sort_order
        """
        query = select(TeamRoleDefinition)
        
        if include_system and tenant_id:
            # Get both system roles AND tenant-specific roles
            query = query.where(
                or_(
                    TeamRoleDefinition.tenant_id.is_(None),
                    TeamRoleDefinition.tenant_id == tenant_id
                )
            )
        elif tenant_id:
            # Only tenant-specific roles
            query = query.where(TeamRoleDefinition.tenant_id == tenant_id)
        elif include_system:
            # Only system roles
            query = query.where(TeamRoleDefinition.tenant_id.is_(None))
            
        query = query.order_by(TeamRoleDefinition.sort_order)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_id(
        self, 
        db: AsyncSession, 
        role_id: UUID
    ) -> Optional[TeamRoleDefinition]:
        """Get team role by ID"""
        result = await db.execute(
            select(TeamRoleDefinition).where(TeamRoleDefinition.id == role_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(
        self, 
        db: AsyncSession, 
        name: str,
        tenant_id: Optional[UUID] = None
    ) -> Optional[TeamRoleDefinition]:
        """
        Get team role by name.
        First checks tenant-specific, then falls back to system role.
        """
        # Check tenant-specific first
        if tenant_id:
            result = await db.execute(
                select(TeamRoleDefinition)
                .where(TeamRoleDefinition.name == name)
                .where(TeamRoleDefinition.tenant_id == tenant_id)
            )
            role = result.scalar_one_or_none()
            if role:
                return role
        
        # Fall back to system role
        result = await db.execute(
            select(TeamRoleDefinition)
            .where(TeamRoleDefinition.name == name)
            .where(TeamRoleDefinition.tenant_id.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def get_default_role(
        self, 
        db: AsyncSession,
        tenant_id: Optional[UUID] = None
    ) -> Optional[TeamRoleDefinition]:
        """Get the default team role for new assignments"""
        # Check tenant-specific default first
        if tenant_id:
            result = await db.execute(
                select(TeamRoleDefinition)
                .where(TeamRoleDefinition.is_default == True)
                .where(TeamRoleDefinition.tenant_id == tenant_id)
            )
            role = result.scalar_one_or_none()
            if role:
                return role
        
        # Fall back to system default
        result = await db.execute(
            select(TeamRoleDefinition)
            .where(TeamRoleDefinition.is_default == True)
            .where(TeamRoleDefinition.tenant_id.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def create_role(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        permissions: List[dict] = None,
        is_default: bool = False
    ) -> TeamRoleDefinition:
        """Create a custom team role for a tenant"""
        if permissions is None:
            permissions = []
            
        role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name=name,
            display_name=display_name,
            description=description,
            permissions=permissions,
            is_system=False,  # Custom roles are never system roles
            is_default=is_default,
            sort_order=100  # Custom roles after system roles
        )
        db.add(role)
        await db.flush()
        await db.refresh(role)
        return role
    
    async def update_role(
        self,
        db: AsyncSession,
        role: TeamRoleDefinition,
        **kwargs
    ) -> TeamRoleDefinition:
        """Update a team role (cannot update system roles)"""
        if role.is_system:
            raise ValueError("Cannot modify system roles")
        
        for key, value in kwargs.items():
            if hasattr(role, key) and key not in ('id', 'tenant_id', 'is_system'):
                setattr(role, key, value)
        
        await db.flush()
        await db.refresh(role)
        return role
    
    async def delete_role(
        self,
        db: AsyncSession,
        role: TeamRoleDefinition
    ) -> bool:
        """Delete a team role (cannot delete system roles)"""
        if role.is_system:
            raise ValueError("Cannot delete system roles")
        
        # Check if role is in use
        from services.b2b.models.team_member import TeamMember
        result = await db.execute(
            select(TeamMember).where(TeamMember.team_role_id == role.id).limit(1)
        )
        if result.scalar_one_or_none():
            raise ValueError("Cannot delete role that is assigned to team members")
        
        await db.delete(role)
        return True


# Singleton instance
team_role_service = TeamRoleService()
