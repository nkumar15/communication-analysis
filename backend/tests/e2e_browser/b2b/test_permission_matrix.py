"""
E2E Browser Tests for Team Role Permission Matrix
Tests the permission matrix UI, resource filtering, and role creation flows
"""
import pytest
from playwright.async_api import Page, expect


@pytest.mark.browser
@pytest.mark.asyncio
class TestPermissionMatrixBrowser:
    """Browser tests for team role permission matrix interface"""
    
    async def test_permission_matrix_displays_only_team_resources(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Permission matrix should only show team resources, not system resources"""
        # Navigate to Team Roles page
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Click Create Custom Role button
        await page.click("text=Create Custom Role")
        
        # Wait for modal to appear
        await page.wait_for_selector(".modal", state="visible")
        
        # Wait for permission matrix to load
        await page.wait_for_selector(".permissions-table", state="visible")
        
        # Verify system resources are NOT displayed
        billing_resource = page.locator("text=Billing")
        await expect(billing_resource).not_to_be_visible()
        
        roles_resource = page.locator("text=Role Management")
        await expect(roles_resource).not_to_be_visible()
        
        audit_logs_resource = page.locator("text=Audit Logs")
        await expect(audit_logs_resource).not_to_be_visible()
        
        # Verify team resources ARE displayed
        users_resource = page.locator("text=User Management")
        await expect(users_resource).to_be_visible()
        
        teams_resource = page.locator("text=Team Management")
        await expect(teams_resource).to_be_visible()
        
        projects_resource = page.locator("text=Projects")
        await expect(projects_resource).to_be_visible()
    
    
    async def test_permission_tooltips_display_on_hover(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Hovering over permission checkboxes should show tooltips"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Open create modal
        await page.click("text=Create Custom Role")
        await page.wait_for_selector(".permissions-table", state="visible")
        
        # Find first checkbox wrapper
        checkbox_wrapper = page.locator(".checkbox-wrapper").first
        
        # Hover over checkbox
        await checkbox_wrapper.hover()
        
        # Wait for tooltip to appear
        tooltip = page.locator(".tooltip-text").first
        await expect(tooltip).to_be_visible()
    
    
    async def test_select_all_permissions_for_resource(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Selecting 'All' checkbox should select all actions for that resource"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Open create modal
        await page.click("text=Create Custom Role")
        await page.wait_for_selector(".permissions-table", state="visible")
        
        # Find the first "Select All" checkbox for a resource
        select_all_checkbox = page.locator(".select-all-cell input[type='checkbox']").first
        
        # Click to select all
        await select_all_checkbox.click()
        
        # Verify that other checkboxes in that row are checked
        # Get the parent row
        row = select_all_checkbox.locator("xpath=ancestor::tr")
        
        # Check that permission cells have checked checkboxes
        permission_checkboxes = row.locator(".permission-cell input[type='checkbox']")
        count = await permission_checkboxes.count()
        
        # All should be checked
        for i in range(count):
            checkbox = permission_checkboxes.nth(i)
            await expect(checkbox).to_be_checked()
    
    
    async def test_create_custom_role_with_permissions(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Create a new custom team role with selected permissions"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Open create modal
        await page.click("text=Create Custom Role")
        await page.wait_for_selector(".modal", state="visible")
        
        # Fill in role details
        await page.fill("input[name='name']", "test_browser_role")
        await page.fill("input[name='display_name']", "Test Browser Role")
        await page.fill("textarea[name='description']", "Created via browser test")
        
        # Select some permissions
        # Click first checkbox in Projects row for 'read' action
        projects_row = page.locator("tr:has-text('Projects')").first
        first_checkbox = projects_row.locator(".permission-cell input[type='checkbox']").first
        await first_checkbox.click()
        
        # Verify permission preview shows selected permission
        preview = page.locator(".selected-permissions-preview")
        await expect(preview).to_contain_text("projects:")
        
        # Submit the form
        await page.click("button:has-text('Create Role')")
        
        # Wait for modal to close and success
        await page.wait_for_selector(".modal", state="hidden")
        
        # Verify the new role appears in the list
        await expect(page.locator("text=Test Browser Role")).to_be_visible()
    
    
    async def test_edit_role_updates_permission_matrix(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Editing a role should pre-populate the permission matrix with existing permissions"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Find a custom role card (not system role) and click edit
        # Assuming there's a role with an edit button
        edit_button = page.locator(".role-card:not(.system-role) button:has-text('Edit')").first
        
        # Check if edit button exists, if not create a role first
        if not await edit_button.is_visible():
            # Create a role first
            await page.click("text=Create Custom Role")
            await page.fill("input[name='name']", "editable_role")
            await page.fill("input[name='display_name']", "Editable Role")
            
            # Select one permission
            first_checkbox = page.locator(".permission-cell input[type='checkbox']").first
            await first_checkbox.click()
            
            await page.click("button:has-text('Create Role')")
            await page.wait_for_selector(".modal", state="hidden")
            
            # Now click edit on the newly created role
            edit_button = page.locator(".role-card:has-text('Editable Role') button:has-text('Edit')").first
        
        await edit_button.click()
        
        # Wait for modal with populated data
        await page.wait_for_selector(".permissions-table", state="visible")
        
        # Verify that some checkboxes are already checked (from existing permissions)
        checked_checkboxes = page.locator(".permission-cell input[type='checkbox']:checked")
        count = await checked_checkboxes.count()
        
        # Should have at least one permission selected
        assert count > 0, "Should have pre-selected permissions when editing"
    
    
    async def test_modal_width_is_900px(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Modal should be 900px wide for better permission matrix visibility"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Open create modal
        await page.click("text=Create Custom Role")
        await page.wait_for_selector(".modal", state="visible")
        
        # Get modal element
        modal = page.locator(".modal").first
        
        # Get computed width
        width = await modal.evaluate("el => window.getComputedStyle(el).maxWidth")
        
        # Should be 900px
        assert width == "900px", f"Expected modal max-width to be 900px, got {width}"
    
    
    async def test_permission_badges_display_on_role_card(
        self,
        page: Page,
        logged_in_b2b_owner
    ):
        """Role cards should display permission badges instead of capability badges"""
        await page.goto("http://localhost:3000/team-roles")
        await page.wait_for_load_state("networkidle")
        
        # Look for role cards
        role_card = page.locator(".role-card").first
        
        # Should have permission-badges section
        permission_section = role_card.locator(".role-permissions")
        await expect(permission_section).to_be_visible()
        
        # Should have heading "Permissions"
        await expect(permission_section.locator("h4")).to_contain_text("Permissions")
        
        # Should have permission badges with resource:action format
        badges = role_card.locator(".permission-badges .badge")
        
        # Check if any badges exist
        count = await badges.count()
        if count > 0:
            # At least one badge should contain ":" (resource:action format)
            first_badge_text = await badges.first.text_content()
            assert ":" in first_badge_text or "No permissions" in first_badge_text
