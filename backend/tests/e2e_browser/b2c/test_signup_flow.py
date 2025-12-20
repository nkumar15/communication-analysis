import pytest
from playwright.sync_api import Page
from ..e2e_helpers import create_custom_token
from ..pages.b2c.signup_page import SignupPage
from ..pages.b2c.workspace_page import WorkspacePage

# No asyncio marker needed now
def test_b2c_signup_flow(page: Page):
    email = "test.b2c.user@example.com"
    # Helper is now sync
    token = create_custom_token(uid="b2c-test-uid", email=email)
    
    signup_page = SignupPage(page)
    workspace_page = WorkspacePage(page)

    # 1. Sign in (Mock Google Auth)
    signup_page.sign_in_with_google_mock(token)

    # 2. Verify Redirect to Dashboard
    signup_page.is_dashboard_visible()

    # 3. Verify Personal Workspace
    # Basic verification that we are in the workspace
    workspace_page.verify_create_workspace_button_visible()
