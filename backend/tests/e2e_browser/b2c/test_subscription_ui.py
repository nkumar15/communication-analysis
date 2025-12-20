from playwright.sync_api import Page
from ..e2e_helpers import create_custom_token
from ..pages.b2c.signup_page import SignupPage
from ..pages.b2c.subscription_page import SubscriptionPage
import secrets
import pytest

def test_subscription_plans_visible(page: Page):
    # 1. Setup User & Login
    email = f"test.sub.{secrets.token_hex(4)}@example.com"
    token = create_custom_token(uid=f"uid-{secrets.token_hex(4)}", email=email)
    
    signup_page = SignupPage(page)
    sub_page = SubscriptionPage(page)

    signup_page.sign_in_with_google_mock(token)
    signup_page.is_dashboard_visible()

    # 2. Navigate to Subscription
    sub_page.navigate()
    sub_page.verify_loaded()

    # 3. Verify Plans (Assuming seed data exists)
    # If these fail, it means we need to seed plans in the test DB
    sub_page.verify_plan_visible("Premium")
    sub_page.verify_plan_visible("Ultimate")
    
    # 4. Verify Upgrade Buttons
    sub_page.verify_upgrade_button_exists("Premium")
