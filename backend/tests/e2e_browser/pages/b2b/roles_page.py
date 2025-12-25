from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class RolesPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.tenant_roles_path = "/roles"
        self.team_roles_path = "/team-roles"

    async def navigate_to_tenant_roles(self):
        url = f"{self.base_url}{self.tenant_roles_path}"
        print(f"DEBUG: Navigating to {url}")
        await self.page.goto(url)
        print(f"DEBUG: Current URL after goto: {self.page.url}")

    async def navigate_to_team_roles(self):
        url = f"{self.base_url}{self.team_roles_path}"
        print(f"DEBUG: Navigating to {url}")
        await self.page.goto(url)
        print(f"DEBUG: Current URL after goto: {self.page.url}")

    async def verify_tenant_roles_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Role Management")
        await expect(self.page.get_by_role("button", name="Create Role")).to_be_visible()

    async def verify_team_roles_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Team Roles")
        await expect(self.page.get_by_role("button", name="Create Custom Role")).to_be_visible()

    # Generic CRUD Helpers
    async def create_role(self, name: str, display_name: str, desc: str, is_team_role: bool = False):
        # Team roles button has "+ " prefix
        button_name = "+ Create Custom Role" if is_team_role else "Create Role"
        
        # Use simple get_by_role with name. Playwright often matches partial, or we use exact string.
        # "Create Role" (system) vs "+ Create Custom Role" (team)
        
        await self.page.get_by_role("button", name=button_name).click(force=True)
        
        # Wait for modal to open
        # Team Roles page uses .modal class
        # System Roles page uses inline styles but has a form inside the modal
        # Verification: Wait for the form to be visible, which is common to both
        await expect(self.page.locator("form")).to_be_visible()
        
        await self.page.fill("input[name='name']", name)
        await self.page.fill("input[name='display_name']", display_name)
        await self.page.fill("textarea[name='description']", desc)
        
        # Use dynamic submit button text
        submit_text = "Create Role"
        if is_team_role: 
            # Team roles modal submit button says "Create Role"
            pass
            
        await self.page.click(f"form button:has-text('{submit_text}')")
        
        # Wait for modal to close
        try:
            await expect(self.page.locator("form")).not_to_be_visible()
        except Exception:
            # If modal is still visible, check for error message
            if await self.page.locator(".alert-error").is_visible():
                error_text = await self.page.locator(".alert-error").inner_text()
                raise AssertionError(f"Role creation failed with backend error: {error_text}")
            # System roles might use .error class in a div
            elif await self.page.locator(".error").is_visible(): 
                error_text = await self.page.locator(".error").inner_text()
                raise AssertionError(f"Role creation failed with backend error: {error_text}")
            raise

    async def delete_role(self, display_name: str):
        # Setup dialog handler before action
        async def handle_dialog(dialog):
            await dialog.accept()

        self.page.on("dialog", handle_dialog)

        # Find the row or card for the role
        if await self.page.locator(f".role-card:has-text('{display_name}')").count() > 0:
            parent = self.page.locator(f".role-card:has-text('{display_name}')")
            # Force click to avoid hover/overlay issues
            await parent.locator("button:has-text('Delete')").click(force=True)
        else:
            parent = self.page.locator(f"tr:has-text('{display_name}')")
            await parent.locator("button:has-text('Delete')").click(force=True)
        
        # Verify gone
        # Wait for success message explicitly. Do NOT swallow error.
        # Check for either alert-success OR system role inline success style (which text matches 'successfully')
        await expect(self.page.locator(".alert-success").or_(self.page.locator("text=successfully"))).to_be_visible(timeout=5000)

        # Then verify item is gone
        await expect(self.page.locator(f"text={display_name}")).not_to_be_visible()
    
    async def edit_role_description(self, display_name: str, new_desc: str):
        if await self.page.locator(f".role-card:has-text('{display_name}')").count() > 0:
            parent = self.page.locator(f".role-card:has-text('{display_name}')")
            await parent.locator("button:has-text('Edit')").click()
        else:
            # Edit not supported/implemented for system roles in this way or different UI
            return

        await expect(self.page.locator(".modal")).to_be_visible()
        
        await self.page.fill("textarea[name='description']", new_desc)
        await self.page.click("button:has-text('Save Changes')") # TeamRole uses 'Save Changes'
        await expect(self.page.locator(".modal")).not_to_be_visible()

    async def verify_role_visible(self, display_name: str):
        # Avoid matching the success alert that contains the display name
        # Team roles are h3 (cards), System roles are td (table) or similar
        # Using .filter(has_not_class="alert") is tricky with generic locator.
        # Better to target relevant structure.
        
        # Try finding it in a card OR table row, but NOT in an alert
        # We can use css :not() pseudo-class if we knew structure better, 
        # or just expect one of the specific containers.
        await expect(
            self.page.locator(f"h3:has-text('{display_name}'), tr:has-text('{display_name}')").first
        ).to_be_visible()

    async def verify_success_message(self, text_fragment: str):
        # Allow partial match since messages vary, but check for green color via styling if possible, 
        # or just presence of alert-success class (Team Roles) or inline style (System Roles)
        # We can look for text within an alert box
        
        # Team Roles uses .alert-success
        # System Roles uses explicit inline style with backgroundColor '#DCFCE7'
        
        # Generic locator for safety: look for text visible
        await expect(self.page.get_by_text(text_fragment)).to_be_visible()
