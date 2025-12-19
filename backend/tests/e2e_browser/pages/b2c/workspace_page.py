from ..base_page import BasePage
from playwright.sync_api import expect

class WorkspacePage(BasePage):
    def verify_workspace_name(self, name: str):
        expect(self.page.get_by_test_id("workspace-name")).to_have_text(name)

    def verify_create_workspace_button_visible(self):
        expect(self.page.get_by_role("button", name="New Workspace")).to_be_visible()

    def create_workspace(self, name: str, type: str = "personal"):
        # Open Modal
        self.page.get_by_role("button", name="New Workspace").click()
        
        # Fill Form
        self.page.get_by_placeholder("e.g., Marketing Team").fill(name)
        self.page.get_by_placeholder("What will you work on").fill(f"Description for {name}")
        
        # Select Type
        if type.lower() == "team":
            self.page.get_by_label("Team").click()
        else:
            self.page.get_by_label("Personal").click()
        
        # Submit
        self.page.get_by_role("button", name="Create Workspace").click()
        
        # Wait for modal to close / success
        expect(self.page.get_by_role("button", name="Create Workspace")).to_be_hidden()

    def verify_workspace_list_contains(self, name: str):
        # Assuming Dashboard lists workspaces. 
        # We can look for the text in a card style or list item.
        expect(self.page.get_by_text(name)).to_be_visible()
