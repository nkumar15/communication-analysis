from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class UsersPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/invitations"  # Redirects to /invitations?activeTab=users

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_loaded(self):
        # Verify Tab is Users
        await expect(self.page.locator("th:has-text('User')")).to_be_visible()
        # Verify at least one user exists (Admin)
        await expect(self.page.locator("tbody tr")).not_to_have_count(0)
    
    async def invite_user(self, email: str):
        # 1. Open Modal
        await self.page.click("button:has-text('Invite User')")
        await expect(self.page.locator("h2:has-text('Invite User')")).to_be_visible()
        
        # 2. Fill Form
        await self.page.fill("input[placeholder='colleague@company.com']", email)
        
        # 3. Send
        await self.page.click("button:has-text('Send Invitation')")
    
    async def verify_invitation_sent(self, email: str):
        await expect(self.page.locator(f"text=Invitation sent to {email}")).to_be_visible()
        await expect(self.page.locator("h2:has-text('Invite User')")).not_to_be_visible()
