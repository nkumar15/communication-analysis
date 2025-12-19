from ..base_page import BasePage
from playwright.sync_api import expect

class WorkspacePage(BasePage):
    def verify_workspace_name(self, name: str):
        expect(self.page.get_by_test_id("workspace-name")).to_have_text(name)

    def verify_create_workspace_button_visible(self):
        expect(self.page.get_by_role("button", name="New Workspace")).to_be_visible()

    def create_team_workspace(self, name: str):
        self.page.get_by_role("button", name="Create Workspace").click()
        self.page.get_by_label("Workspace Name").fill(name)
        self.page.get_by_role("button", name="Create").click()
