from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class RolesPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.tenant_roles_path = "/b2b/roles"
        self.team_roles_path = "/b2b/team-roles"

    async def navigate_to_tenant_roles(self):
        await self.page.goto(f"{self.base_url}{self.tenant_roles_path}")

    async def navigate_to_team_roles(self):
        await self.page.goto(f"{self.base_url}{self.team_roles_path}")

    async def verify_tenant_roles_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Role Management")
        await expect(self.page.locator("button:has-text('Create Role')")).to_be_visible()
        await expect(self.page.locator("text=Owner").first).to_be_visible()
        await expect(self.page.locator("text=Admin").first).to_be_visible()

    async def verify_team_roles_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Team Roles")
        await expect(self.page.locator("button:has-text('+ Create Custom Role')")).to_be_visible()
        await expect(self.page.locator("h3:has-text('Team Admin')")).to_be_visible()
        await expect(self.page.locator("h3:has-text('Member')")).to_be_visible()

    async def create_team_role(self, name: str, display_name: str, desc: str):
        await self.page.click("button:has-text('+ Create Custom Role')")
        await expect(self.page.locator(".modal")).to_be_visible()
        
        await self.page.fill("input[name='name']", name)
        await self.page.fill("input[name='display_name']", display_name)
        await self.page.fill("textarea[name='description']", desc)
        
        await self.page.click("button:has-text('Create Role')")

    async def verify_role_created(self, display_name: str):
        await expect(self.page.locator("h2:has-text('Create Custom Team Role')")).not_to_be_visible()
        await expect(self.page.locator(f"h3:has-text('{display_name}')")).to_be_visible()

    async def verify_permission_badges(self):
        role_card = self.page.locator(".role-card:not(.system-role)").first
        if await role_card.count() > 0:
            await expect(role_card.locator("h4:has-text('Permissions')")).to_be_visible()
            await expect(role_card.locator(".badge").first).to_be_visible()
    
    # Permission Matrix Helpers
    async def open_create_role_modal_and_check_matrix(self):
        await self.page.click("button:has-text('+ Create Custom Role')")
        await expect(self.page.locator(".modal")).to_be_visible()
        
        # Verify Resource Filtering
        await expect(self.page.locator("text=Billing")).not_to_be_visible()
        await expect(self.page.locator("text=Role Management")).not_to_be_visible()
        await expect(self.page.locator("text=User Management")).to_be_visible()
        await expect(self.page.locator("text=Projects")).to_be_visible()

    async def verify_matrix_tooltips(self):
        checkbox = self.page.locator(".checkbox-wrapper").first
        if await checkbox.is_visible():
            await checkbox.hover()
            await expect(self.page.locator(".tooltip-text").first).to_be_visible()

    async def verify_matrix_select_all(self):
        select_all = self.page.locator(".select-all-cell input[type='checkbox']").first
        if await select_all.is_visible():
            await select_all.click()
            row = select_all.locator("xpath=ancestor::tr")
            permission_checkboxes = row.locator(".permission-cell input[type='checkbox']")
            
            count = await permission_checkboxes.count()
            for i in range(count):
                await expect(permission_checkboxes.nth(i)).to_be_checked()
