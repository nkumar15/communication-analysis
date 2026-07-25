from playwright.async_api import Page, Locator, expect

class AsyncBasePage:
    """Base Page Object for Async Playwright tests"""
    def __init__(self, page: Page):
        self.page = page

    async def navigate(self, path: str):
        """Navigate to a relative path"""
        await self.page.goto(path)

    async def wait_for_url(self, path_pattern: str, timeout: int = 5000):
        """Wait for URL to match pattern"""
        await self.page.wait_for_url(f"**{path_pattern}", timeout=timeout)

    async def reload(self):
        await self.page.reload()
    
    def get_by_testid(self, testid: str) -> Locator:
        return self.page.get_by_test_id(testid)
    
    async def get_title(self) -> str:
        return await self.page.title()
