from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class TeamsPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/b2b/teams"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Teams")
        await expect(self.page.locator("text=Total Teams")).to_be_visible()
        await expect(self.page.locator("text=My Teams")).to_be_visible()

    async def verify_default_team_exists(self):
        await expect(self.page.locator("text=Default").first).to_be_visible()

    async def create_team(self, name: str, description: str):
        await self.page.click("button:has-text('Create Team')")
        await expect(self.page.locator("h2:has-text('Create New Team')")).to_be_visible()
        
        await self.page.fill("input[name='team-name']", name)
        await self.page.fill("textarea[name='team-desc']", description)
        
        await self.page.click("button:has-text('✨ Create Team')")

    async def verify_team_created(self, name: str):
        await expect(self.page.locator("h2:has-text('Create New Team')")).not_to_be_visible()
        await expect(self.page.locator(f"h3:has-text('{name}')")).to_be_visible()
