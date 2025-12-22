from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class LoginPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/login"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_on_login_page(self):
        await expect(self.page.locator("h1")).to_contain_text("Enterprise SSO Portal")
    
    async def login_with_custom_token(self, custom_token: str):
        """
        Injects custom token via localStorage and reloads to trigger auto-login.
        """
        print(f"Injecting custom token via localStorage...")
        await self.page.evaluate(f"localStorage.setItem('custom_token', '{custom_token}')")
        await self.reload()
    
    async def verify_login_error(self, error_text: str):
        error_msg = self.page.locator(".error-message")
        await expect(error_msg).to_be_visible()
        await expect(error_msg).to_contain_text(error_text)
