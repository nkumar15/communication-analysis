from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage
import re

class DashboardPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/dashboard"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Dashboard")
        await expect(self.page.locator("body")).to_contain_text("Overview")

    async def verify_stats_cards(self, count: int = 4):
        stats_cards = self.page.locator(".stats-card, [data-testid='stats-card']")
        await expect(stats_cards).to_have_count(count)
    
    async def verify_recent_activity(self):
        await expect(self.page.locator("text=Recent Activity")).to_be_visible()

    async def navigate_to_users(self):
        # Click shortcut or sidebar
        await self.page.click("nav a[href='/b2b/users']")
        await expect(self.page).to_have_url(re.compile(r"/b2b/users"))
