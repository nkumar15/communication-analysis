from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class AuditLogsPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/b2b/audit-logs"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Audit Logs")
        await expect(self.page.locator("select[name='event_type']")).to_be_visible()
        await expect(self.page.locator("th:has-text('Event')")).to_be_visible()
        await expect(self.page.locator("th:has-text('Actor')")).to_be_visible()
        await expect(self.page.locator("button:has-text('Export CSV')")).to_be_visible()
