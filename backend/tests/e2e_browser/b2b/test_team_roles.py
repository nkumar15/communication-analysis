"""Team Roles Page E2E Tests"""
import pytest
from playwright.async_api import expect, Page
from tests.e2e_browser.pages.b2b.roles_page import RolesPage
import time

@pytest.mark.asyncio
@pytest.mark.browser
async def test_team_roles_crud(authenticated_b2b_page: Page, b2b_test_setup):
    """
    Test Team Roles CRUD operations.
    1. Navigate to Team Roles
    2. Create a new custom team role
    3. Update the role
    4. Delete the role
    """
    roles_page = RolesPage(authenticated_b2b_page)
    timestamp = int(time.time())
    # Role name must match ^[a-z_]+$ (lowercase letters and underscores only, NO DIGITS)
    # Using hex from uuid or similar, mapping digits to letters to be safe? 
    # Or just a fixed prefix + short alpha string.
    # Let's use a simple mapping or just "test_role_custom"
    
    unique_suffix = f"{timestamp}"
    # Simple hack: map digits to letters a-j
    alpha_suffix = "".join([chr(ord('a') + int(d)) for d in unique_suffix])
    
    role_name = f"test_role_{alpha_suffix}"
    display_name = f"Test Role {timestamp}"
    description = "Test description for team role"
    new_description = "Updated description for team role"

    # 1. Navigate
    # Ensure we assume base_url is set up correct relative to dashboard or provided
    # The fixture authenticated_b2b_page is already at dashboard usually
    # roles_page.base_url might need adjustment if logic in RolesPage.__init__ is hardcoded to localhost:3000
    # but we will rely on relative navigation if possible or just use the method which constructs full url
    # Let's align base_url with page.url
    base_url = authenticated_b2b_page.url.split('/dashboard')[0] if '/dashboard' in authenticated_b2b_page.url else authenticated_b2b_page.url.rstrip('/')
    roles_page.base_url = base_url

    await roles_page.navigate_to_team_roles()
    await roles_page.verify_team_roles_loaded()

    # 2. Create
    await roles_page.create_role(
        name=role_name,
        display_name=display_name,
        desc=description,
        is_team_role=True
    )
    await roles_page.verify_success_message("created successfully")
    await roles_page.verify_role_visible(display_name)

    # 3. Update (Description)
    await roles_page.edit_role_description(display_name, new_description)
    await roles_page.verify_success_message("updated successfully")
    
    # 4. Delete
    await roles_page.delete_role(display_name)
    # Success already verified in delete_role mechanism to ensure timing is caught
    
    # Verify deletion
    await expect(authenticated_b2b_page.locator(f"text={display_name}")).not_to_be_visible()
