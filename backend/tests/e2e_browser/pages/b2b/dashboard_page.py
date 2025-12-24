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

    async def verify_heading_interactive(self):
        """
        Verify heading is interactive (matches recording: page.get_by_role("heading", name="Dashboard").click())
        """
        heading = self.page.get_by_role("heading", name="Dashboard")
        await expect(heading).to_be_visible()
        await heading.click()
