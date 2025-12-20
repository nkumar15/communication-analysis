from ..base_page import BasePage
from playwright.sync_api import expect

class BillingHistoryPage(BasePage):
    def verify_loaded(self):
        expect(self.page.get_by_role("heading", name="Billing History")).to_be_visible()
