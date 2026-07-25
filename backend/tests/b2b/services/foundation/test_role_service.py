"""
Service Layer Tests: RoleService

Tests for tenant-specific role management business logic.
Covers: CRUD operations, permission binding, system role protection.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException

from modules.b2b.services.role_service import role_service
from modules.b2b.models import Role, RolePermission, Resource, Action
from modules.b2b.schemas.roles import RoleCreate, RoleUpdate
from tests.conftest import set_tenant_context


pytestmark = pytest.mark.asyncio


class TestRoleServiceCRUD:
    """Tests for basic role CRUD operations"""
    
    async def test_create_role_with_permissions(self, db_session, b2b_test_setup):
        """Test creating a custom role with explicit permissions"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Fetch a real resource and action to use
        resources = await role_service.get_all_resources(session)
        actions = await role_service.get_all_actions(session)
        
        if not resources or not actions:
            pytest.skip("No resources or actions seeded for permissions")
        
        role_data = RoleCreate(
            name=f"test_analyst_{uuid4().hex[:6]}",
            display_name="Test Analyst",
            description="A test analyst role",
            permissions=[
                {"resource_id": str(resources[0].id), "action_id": str(actions[0].id)}
            ]
        )
        
        # Act
        role = await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Assert
        assert role is not None
        assert role.name == role_data.name
        assert role.tenant_id == tenant_id
        assert role.is_system_role is False
        assert len(role.permissions) >= 1
    
    async def test_create_role_duplicate_name_fails(self, db_session, b2b_test_setup):
        """Test that creating a role with duplicate name raises error"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        unique_name = f"duplicate_role_{uuid4().hex[:6]}"
        role_data = RoleCreate(
            name=unique_name,
            display_name="First Role",
            description="First version"
        )
        
        # Create first role
        await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Act & Assert - second creation should fail
        duplicate_data = RoleCreate(
            name=unique_name,
            display_name="Second Role",
            description="Duplicate name"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await role_service.create_role(session, tenant_id, duplicate_data)
        
        assert exc_info.value.status_code == 409
        assert "already exists" in str(exc_info.value.detail)
    
    async def test_get_all_roles_returns_tenant_roles(self, db_session, b2b_test_setup):
        """Test listing roles returns only tenant-specific roles"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a role to ensure at least one exists
        role_data = RoleCreate(
            name=f"list_test_role_{uuid4().hex[:6]}",
            display_name="List Test Role"
        )
        await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Act
        roles = await role_service.get_all_roles(session, tenant_id)
        
        # Assert
        assert len(roles) >= 1
        for role in roles:
            assert role.tenant_id == tenant_id
            assert role.deleted_at is None
    
    async def test_get_role_by_id(self, db_session, b2b_test_setup):
        """Test fetching a single role by ID"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role_data = RoleCreate(
            name=f"fetch_test_role_{uuid4().hex[:6]}",
            display_name="Fetch Test Role"
        )
        created_role = await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Act
        fetched_role = await role_service.get_role_by_id(session, created_role.id)
        
        # Assert
        assert fetched_role is not None
        assert fetched_role.id == created_role.id
        assert fetched_role.name == created_role.name
    
    async def test_get_role_by_name(self, db_session, b2b_test_setup):
        """Test fetching a role by name within tenant"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        unique_name = f"name_lookup_{uuid4().hex[:6]}"
        role_data = RoleCreate(
            name=unique_name,
            display_name="Name Lookup Role"
        )
        await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Act
        fetched_role = await role_service.get_role_by_name(session, unique_name, tenant_id)
        
        # Assert
        assert fetched_role is not None
        assert fetched_role.name == unique_name


class TestRoleServiceUpdate:
    """Tests for role update operations"""
    
    async def test_update_role_display_name(self, db_session, b2b_test_setup):
        """Test updating a role's display name"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role_data = RoleCreate(
            name=f"update_test_{uuid4().hex[:6]}",
            display_name="Original Name"
        )
        role = await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        
        # Act
        update_data = RoleUpdate(display_name="Updated Name")
        updated_role = await role_service.update_role(session, role, update_data)
        await session.commit()
        
        # Assert
        assert updated_role.display_name == "Updated Name"
    
    async def test_update_system_role_forbidden(self, db_session, b2b_test_setup):
        """Test that updating a system role raises 403"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Find a system role
        result = await session.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.is_system_role == True
            )
        )
        system_role = result.scalars().first()
        
        if not system_role:
            pytest.skip("No system roles found in tenant")
        
        # Act & Assert
        update_data = RoleUpdate(display_name="Hacked Name")
        
        with pytest.raises(HTTPException) as exc_info:
            await role_service.update_role(session, system_role, update_data)
        
        assert exc_info.value.status_code == 403
        assert "system roles" in str(exc_info.value.detail).lower()


class TestRoleServiceDelete:
    """Tests for role deletion operations"""
    
    async def test_delete_role_soft_delete(self, db_session, b2b_test_setup):
        """Test that deleting a role performs soft delete"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        role_data = RoleCreate(
            name=f"delete_test_{uuid4().hex[:6]}",
            display_name="To Be Deleted"
        )
        created_role = await role_service.create_role(session, tenant_id, role_data)
        await session.commit()
        role_id = created_role.id
        
        # Re-fetch to ensure the role is attached to the session
        role = await role_service.get_role_by_id(session, role_id)
        
        # Act
        await role_service.delete_role(session, role)
        await session.commit()
        
        # Assert - role should still exist but be soft-deleted
        # Need to expire cache to see the updated deleted_at
        session.expire_all()
        result = await session.execute(
            select(Role).where(Role.id == role_id)
        )
        deleted_role = result.scalars().first()
        
        assert deleted_role is not None
        assert deleted_role.deleted_at is not None
    
    async def test_delete_system_role_forbidden(self, db_session, b2b_test_setup):
        """Test that deleting a system role raises 400"""
        # Arrange
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Find a system role
        result = await session.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.is_system_role == True
            )
        )
        system_role = result.scalars().first()
        
        if not system_role:
            pytest.skip("No system roles found in tenant")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await role_service.delete_role(session, system_role)
        
        assert exc_info.value.status_code == 400
        assert "system roles" in str(exc_info.value.detail).lower()


class TestRoleServiceMetadata:
    """Tests for role metadata endpoints (resources, actions)"""
    
    async def test_get_all_resources(self, db_session, b2b_test_setup):
        """Test fetching all available resources"""
        # Arrange
        session = b2b_test_setup["session"]
        
        # Act
        resources = await role_service.get_all_resources(session)
        
        # Assert
        assert isinstance(resources, list)
        # Resources should be seeded
        if resources:
            assert hasattr(resources[0], 'id')
            assert hasattr(resources[0], 'name')
    
    async def test_get_all_actions(self, db_session, b2b_test_setup):
        """Test fetching all available actions"""
        # Arrange
        session = b2b_test_setup["session"]
        
        # Act
        actions = await role_service.get_all_actions(session)
        
        # Assert
        assert isinstance(actions, list)
        # Actions should be seeded
        if actions:
            assert hasattr(actions[0], 'id')
            assert hasattr(actions[0], 'name')
