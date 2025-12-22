from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class SettingsPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/settings/account"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Account Settings")

    async def update_org_name(self, new_name: str):
        # Fill name
        await self.page.fill("input[value*='Test Company'], input[value*='Updated Test Company']", new_name)
        # Save
        await self.page.click("button:has-text('Save Changes')")

    async def verify_success_message(self):
        await expect(self.page.locator("text=Account settings updated successfully")).to_be_visible()

    async def verify_org_name_persisted(self, name: str):
        await expect(self.page.locator(f"input[value='{name}']")).to_be_visible()

    async def verify_sso_config_visible(self):
        await expect(self.page.locator("h2:has-text('SSO Configuration')")).to_be_visible()
        await expect(self.page.locator("button:has-text('Edit Credentials')")).to_be_visible()
