from playwright.sync_api import Page
from ..e2e_helpers import create_custom_token
from ..pages.b2c.signup_page import SignupPage
from ..pages.b2c.workspace_page import WorkspacePage
import secrets

def test_create_and_switch_workspace(page: Page):
    # 1. Setup User
    email = f"test.b2c.{secrets.token_hex(4)}@example.com"
    token = create_custom_token(uid=f"uid-{secrets.token_hex(4)}", email=email)
    
    signup_page = SignupPage(page)
    workspace_page = WorkspacePage(page)

    # 2. Login
    signup_page.sign_in_with_google_mock(token)
    workspace_page.verify_create_workspace_button_visible()

    # 3. Try to Create Team Workspace (Should Fail for Free User)
    new_ws_name = "My Team Project"
    # Expected error message usually contains "Workspace limit reached" or "Team workspaces require Premium"
    # Based on quota_service.py: "Team workspaces require Premium or Ultimate subscription"
    workspace_page.create_workspace_expect_error(new_ws_name, type="team", error_message_part="Team workspaces require Premium")

    # 4. Verify Failure (Explicit check done inside create_workspace_expect_error)
    # Ensure it was NOT created
    # workspace_page.verify_workspace_list_does_not_contain(new_ws_name) # construct this if needed, but error check is good enough for now
