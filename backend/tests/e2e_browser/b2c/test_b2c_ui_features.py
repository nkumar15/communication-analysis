from playwright.sync_api import Page, expect
from ..e2e_helpers import create_custom_token
from ..pages.b2c.signup_page import SignupPage
from ..pages.b2c.settings_page import SettingsPage
from ..pages.b2c.billing_history_page import BillingHistoryPage
import secrets

def test_user_menu_navigation(page: Page):
    # 1. Setup User
    email = f"test.ui.{secrets.token_hex(4)}@example.com"
    token = create_custom_token(uid=f"uid-{secrets.token_hex(4)}", email=email)
    
    signup_page = SignupPage(page)
    settings_page = SettingsPage(page)
    billing_page = BillingHistoryPage(page)

    # 2. Login
    signup_page.sign_in_with_google_mock(token)
    signup_page.is_dashboard_visible()

    # 3. Open User Menu
    # The user menu button displays the user's name/email.
    page.get_by_test_id("user-menu-trigger").click()

    # 4. Navigate to Settings
    # Menu is open, click "Settings"
    page.get_by_role("button", name="Settings").click()
    settings_page.verify_loaded()

    # 5. Open User Menu again and Navigate to Billing History
    page.get_by_test_id("user-menu-trigger").click()
    page.get_by_role("button", name="Billing History").click()
    billing_page.verify_loaded()
