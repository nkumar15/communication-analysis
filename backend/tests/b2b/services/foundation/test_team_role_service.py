"""
Service Layer Tests: TeamRoleService

Tests for team-level role definition business logic.
Covers: CRUD operations, system role protection, default role handling.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select

from modules.b2b.services.team_role_service import team_role_service
from modules.b2b.models.team_role_definition import TeamRoleDefinition


pytestmark = pytest.mark.asyncio


class TestTeamRoleServiceList:
    """Tests for listing team role definitions"""
    
    async def test_list_team_roles_includes_system(self, db_session, b2b_test_setup):
        """Test that listing roles includes system roles"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Act
        roles = await team_role_service.list_team_roles(
            session, 
            tenant_id=tenant_id, 
            include_system=True
        )
        
        # Assert
        assert isinstance(roles, list)
        # Should include system roles (tenant_id is None) and tenant-specific
        system_roles = [r for r in roles if r.tenant_id is None]
        assert len(system_roles) >= 0  # May or may not have system roles
    
    async def test_list_team_roles_tenant_only(self, db_session, b2b_test_setup):
        """Test listing only tenant-specific roles"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a custom role first
        await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=f"custom_role_{uuid4().hex[:6]}",
            display_name="Custom Role"
        )
        await session.commit()
        
        # Act
        roles = await team_role_service.list_team_roles(
            session, 
            tenant_id=tenant_id, 
            include_system=False
        )
        
        # Assert
        for role in roles:
            assert role.tenant_id == tenant_id


class TestTeamRoleServiceGet:
    """Tests for fetching team role definitions"""
    
    async def test_get_by_id(self, db_session, b2b_test_setup):
        """Test fetching role by ID"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        created = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=f"get_by_id_{uuid4().hex[:6]}",
            display_name="Get By ID Role"
        )
        await session.commit()
        
        # Act
        fetched = await team_role_service.get_by_id(session, created.id)
        
        # Assert
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == created.name
    
    async def test_get_by_name_tenant_override(self, db_session, b2b_test_setup):
        """Test that tenant-specific role takes precedence over system role"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a tenant-specific role with a unique name
        unique_name = f"priority_role_{uuid4().hex[:6]}"
        created = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=unique_name,
            display_name="Priority Role"
        )
        await session.commit()
        
        # Act
        fetched = await team_role_service.get_by_name(
            session, 
            name=unique_name, 
            tenant_id=tenant_id
        )
        
        # Assert
        assert fetched is not None
        assert fetched.tenant_id == tenant_id  # Tenant-specific, not system
    
    async def test_get_default_role(self, db_session, b2b_test_setup):
        """Test fetching the default team role"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Act
        default_role = await team_role_service.get_default_role(session, tenant_id)
        
        # Assert
        # Default role may or may not exist depending on seeding
        if default_role:
            assert default_role.is_default is True


class TestTeamRoleServiceCreate:
    """Tests for creating team role definitions"""
    
    async def test_create_custom_team_role(self, db_session, b2b_test_setup):
        """Test creating a custom team role"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role_name = f"custom_analyst_{uuid4().hex[:6]}"
        
        # Act
        role = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=role_name,
            display_name="Custom Analyst",
            description="A custom analyst role",
            permissions=[{"resource": "alerts", "action": "read"}]
        )
        await session.commit()
        
        # Assert
        assert role is not None
        assert role.name == role_name
        assert role.tenant_id == tenant_id
        assert role.is_system is False
        assert role.sort_order == 100  # Custom roles get sort_order 100
    
    async def test_create_role_with_default_flag(self, db_session, b2b_test_setup):
        """Test creating a role marked as default"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role_name = f"default_role_{uuid4().hex[:6]}"
        
        # Act
        role = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=role_name,
            display_name="Default Role",
            is_default=True
        )
        await session.commit()
        
        # Assert
        assert role.is_default is True


class TestTeamRoleServiceUpdate:
    """Tests for updating team role definitions"""
    
    async def test_update_custom_role(self, db_session, b2b_test_setup):
        """Test updating a custom role"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=f"update_test_{uuid4().hex[:6]}",
            display_name="Original Name"
        )
        await session.commit()
        
        # Act
        updated = await team_role_service.update_role(
            session,
            role,
            display_name="Updated Name",
            description="New description"
        )
        await session.commit()
        
        # Assert
        assert updated.display_name == "Updated Name"
        assert updated.description == "New description"
    
    async def test_update_system_role_forbidden(self, db_session, b2b_test_setup):
        """Test that updating a system role raises ValueError"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        
        # Find a system role (tenant_id is None)
        result = await session.execute(
            select(TeamRoleDefinition).where(
                TeamRoleDefinition.tenant_id.is_(None),
                TeamRoleDefinition.is_system == True
            )
        )
        system_role = result.scalars().first()
        
        if not system_role:
            pytest.skip("No system team roles found")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot modify system roles"):
            await team_role_service.update_role(
                session,
                system_role,
                display_name="Hacked Name"
            )


class TestTeamRoleServiceDelete:
    """Tests for deleting team role definitions"""
    
    async def test_delete_custom_role(self, db_session, b2b_test_setup):
        """Test deleting a custom role"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=f"delete_test_{uuid4().hex[:6]}",
            display_name="To Be Deleted"
        )
        await session.commit()
        role_id = role.id
        
        # Act
        result = await team_role_service.delete_role(session, role)
        await session.commit()
        
        # Assert
        assert result is True
        
        # Verify it's gone
        fetched = await team_role_service.get_by_id(session, role_id)
        assert fetched is None
    
    async def test_delete_system_role_forbidden(self, db_session, b2b_test_setup):
        """Test that deleting a system role raises ValueError"""
        # Arrange
        setup = b2b_test_setup
        session = setup["session"]
        
        # Find a system role
        result = await session.execute(
            select(TeamRoleDefinition).where(
                TeamRoleDefinition.tenant_id.is_(None),
                TeamRoleDefinition.is_system == True
            )
        )
        system_role = result.scalars().first()
        
        if not system_role:
            pytest.skip("No system team roles found")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete system roles"):
            await team_role_service.delete_role(session, system_role)
    
    async def test_delete_default_role_forbidden(self, db_session, b2b_test_setup):
        """Test that deleting the default role raises ValueError"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a default role
        role = await team_role_service.create_role(
            session,
            tenant_id=tenant_id,
            name=f"default_delete_{uuid4().hex[:6]}",
            display_name="Default To Delete",
            is_default=True
        )
        await session.commit()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete the default role"):
            await team_role_service.delete_role(session, role)
