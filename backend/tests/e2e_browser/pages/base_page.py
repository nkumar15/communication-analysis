from playwright.sync_api import Page, Locator, expect

class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def navigate(self, path: str):
        """Navigate to a relative path"""
        self.page.goto(path)

    def wait_for_url(self, path_pattern: str, timeout: int = 5000):
        """Wait for URL to match pattern"""
        self.page.wait_for_url(f"**{path_pattern}", timeout=timeout)

    def reload(self):
        self.page.reload()
    
    def get_by_testid(self, testid: str) -> Locator:
        return self.page.get_by_test_id(testid)
