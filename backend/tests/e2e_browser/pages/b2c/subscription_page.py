from ..base_page import BasePage
from ...e2e_config import FRONTEND_URL_B2C
from playwright.sync_api import expect

class SubscriptionPage(BasePage):
    def navigate(self):
        self.page.goto(f"{FRONTEND_URL_B2C}/subscription")

    def verify_loaded(self):
        expect(self.page.get_by_role("heading", name="Choose Your Plan")).to_be_visible()

    def verify_plan_visible(self, plan_name: str):
        # Look for the plan name heading
        expect(self.page.get_by_role("heading", name=plan_name, exact=True)).to_be_visible()

    def verify_upgrade_button_exists(self, plan_name: str):
        # Button text format "Upgrade to {plan_name}"
        expect(self.page.get_by_role("button", name=f"Upgrade to {plan_name}")).to_be_visible()
