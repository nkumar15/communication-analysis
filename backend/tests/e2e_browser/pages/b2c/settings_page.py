from ..base_page import BasePage
from playwright.sync_api import expect

class SettingsPage(BasePage):
    def verify_loaded(self):
        expect(self.page.get_by_role("heading", name="Account Settings")).to_be_visible()
