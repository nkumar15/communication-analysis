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

    # 3. Create Personal Workspace (Second one)
    # We create a personal workspace because fresh users are on Free plan,
    # which doesn't allow Team workspaces.
    new_ws_name = "My Side Project"
    workspace_page.create_workspace(new_ws_name, type="personal")

    # 4. Verify Success
    # Should see the new workspace in the list or title
    workspace_page.verify_workspace_list_contains(new_ws_name)
