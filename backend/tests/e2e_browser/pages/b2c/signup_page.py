from ..base_page import BasePage
from playwright.sync_api import expect

from ...e2e_config import FRONTEND_URL_B2C

class SignupPage(BasePage):
    def navigate(self):
        self.page.goto(f"{FRONTEND_URL_B2C}/login")

    def sign_in_with_google_mock(self, token: str):
        """
        Simulate Google Sign-In by injecting a custom token.
        This bypasses the popup flow.
        """
        # Inject token into localStorage (simulating the result of a popup)
        # We must navigate to the B2C App specifically
        self.page.goto(f"{FRONTEND_URL_B2C}/login")
        self.page.evaluate(f"localStorage.setItem('custom_token', '{token}')")
        self.page.reload()
        
    def complete_onboarding(self, display_name: str):
        """
        If there's an onboarding step after signup (e.g. set name), handle it here.
        """
        # Wait for "Welcome" or "Setup"
        pass
    
    def is_dashboard_visible(self):
        # Wait for redirect to home/dashboard
        self.page.wait_for_url("**/", timeout=10000)
        
        # Check for generic dashboard elements
        expect(self.page.get_by_role("button", name="New Workspace")).to_be_visible()
