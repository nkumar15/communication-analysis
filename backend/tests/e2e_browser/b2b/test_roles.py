from playwright.async_api import Page
import pytest
import os
from tests.e2e_browser.pages.b2b.roles_page import RolesPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_tenant_roles_load(authenticated_b2b_page: Page):
    """
    Test that the Tenant Roles page loads and displays roles.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    roles_page = RolesPage(authenticated_b2b_page, base_url)
    
    await roles_page.navigate_to_tenant_roles()
    await roles_page.verify_tenant_roles_loaded()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_team_roles_load(authenticated_b2b_page: Page):
    """
    Test that the Team Roles page loads and displays roles.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    roles_page = RolesPage(authenticated_b2b_page, base_url)
    
    await roles_page.navigate_to_team_roles()
    await roles_page.verify_team_roles_loaded()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_create_team_role(authenticated_b2b_page: Page):
    """
    Test creating a new custom team role.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    roles_page = RolesPage(authenticated_b2b_page, base_url)
    
    await roles_page.navigate_to_team_roles()
    
    role_name = "QA Lead"
    await roles_page.create_team_role("qa_lead", role_name, "Role for QA Leads")
    
    await roles_page.verify_role_created(role_name)

@pytest.mark.browser
@pytest.mark.asyncio
async def test_permission_matrix_interactions(authenticated_b2b_page: Page):
    """
    Test interaction with the permission matrix (filtering, tooltips, select all).
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    roles_page = RolesPage(authenticated_b2b_page, base_url)
    
    await roles_page.navigate_to_team_roles()
    
    await roles_page.open_create_role_modal_and_check_matrix()
    await roles_page.verify_matrix_tooltips()
    await roles_page.verify_matrix_select_all()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_role_permissions_display(authenticated_b2b_page: Page):
    """
    Test that created roles show correct permission badges.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    roles_page = RolesPage(authenticated_b2b_page, base_url)
    
    await roles_page.navigate_to_team_roles()
    await roles_page.verify_permission_badges()
