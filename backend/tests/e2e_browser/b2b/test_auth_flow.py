import pytest
import os
from playwright.async_api import Page, expect
from tests.e2e_browser.pages.b2b.login_page import LoginPage
from tests.e2e_browser.pages.b2b.dashboard_page import DashboardPage
from infrastructure.auth import get_auth_provider

# Initialize Firebase Admin SDK (idempotent)
get_auth_provider().initialize()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_login_flow_with_custom_token(async_page: Page, b2b_test_setup):
    """
    Test the full login flow using Custom Token injection (bypass UI providers).
    Uses Page Object Model.
    """
    from firebase_admin import auth
    
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # 1. Get test user from fixture
    user = b2b_test_setup["admin"]
    tenant = b2b_test_setup["tenant"]
    
    # Mint Custom Token
    custom_token = auth.create_custom_token(user.firebase_uid, developer_claims={
        "tenant": tenant.firebase_tenant_id
    }).decode('utf-8')
    
    # 2. Use LoginPage
    login_page = LoginPage(async_page, base_url)
    await login_page.navigate()
    await login_page.verify_on_login_page()
    
    # 3. Perform Login
    await login_page.login_with_custom_token(custom_token)

    # 4. Verify Dashboard
    dashboard_page = DashboardPage(async_page, base_url)
    # Wait for URL redirect
    await dashboard_page.wait_for_url("/dashboard", timeout=15000)
    await dashboard_page.verify_loaded()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_login_validation(async_page: Page):
    """Test login form validation without auth"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    login_page = LoginPage(async_page, base_url)
    
    await login_page.navigate()
    
    # Try empty submit
    submit_btn = async_page.locator("button[type='submit']")
    await expect(submit_btn).to_be_disabled()
    
    # Enter invalid email
    await async_page.fill("#email", "invalid-email")
    await expect(submit_btn).to_be_disabled()
    
    # Enter valid email format but non-existent
    await async_page.fill("#email", "nonexistent@example.com")
    await async_page.click("button[type='submit']")
    
    # Should show error message
    await login_page.verify_login_error("Tenant not found")
