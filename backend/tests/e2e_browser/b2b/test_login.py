"""Login Page E2E Tests"""
import pytest
from playwright.async_api import expect, Page
import os


@pytest.mark.asyncio
@pytest.mark.browser
async def test_sso_login(async_page: Page):
    """Test SSO login flow with popup and profile verification"""
    from ..pages.b2b.login_page import LoginPage
    
    # Get credentials from environment
    email = os.getenv("B2B_OWNER_EMAIL", "owner@firstcompany.net")
    password = os.getenv("B2B_OWNER_PASSWORD", "owner01-pwd")
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Perform SSO login
    login_page = LoginPage(async_page, base_url)
    await login_page.login_with_sso(email, password)
    
    # Verify we're on dashboard
    assert "/dashboard" in async_page.url
    
    # Page has main heading
    await expect(async_page.locator("h1")).to_be_visible(timeout=5000)
    
    # No error messages
    error_locator = async_page.locator(".error-message, .alert-error, [role='alert'][class*='error']")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)
    
    # Verify profile menu interactions (from original recording)
    print("🔍 Verifying profile menu...")
    
    # Click profile button (should show user email)
    profile_button = async_page.get_by_role("button", name=f"O {email} owner")
    await profile_button.click()
    print("✅ Clicked profile button")
    
    # Verify profile menu is visible with user info
    # Use nth(1) because email appears in: 1) Profile Button, 2) Menu Header, 3) Menu Item
    await expect(async_page.get_by_text(email).nth(1)).to_be_visible(timeout=10000)
    print("✅ Profile menu visible with user email")
    
    # Click to view different parts of profile info
    await async_page.get_by_text(email).nth(2).click()
    print("✅ Clicked profile email")
    
    # Verify owner role is displayed
    await async_page.get_by_text("owner", exact=True).nth(1).click()
    print("✅ Verified owner role")
    
    # Close profile menu by clicking button again
    await async_page.get_by_role("button", name=f"O {email} owner").click()
    print("✅ Closed profile menu")
    
    print("✅ SSO login test completed successfully!")


# TODO: Add more login-specific tests as needed
# async def test_sso_login_invalid_credentials():
# async def test_login_error_messages():
