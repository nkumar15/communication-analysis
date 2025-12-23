"""Dashboard E2E Tests"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_dashboard_loads(authenticated_b2b_page: Page, b2b_test_setup):
    """Verify dashboard page loads with user data"""
    page = authenticated_b2b_page
    
    # Verify we're on dashboard (not login page)
    assert "/login" not in page.url
    
    # Page has main heading
    await expect(page.locator("h1")).to_be_visible(timeout=5000)
    
    # No error messages
    error_locator = page.locator(".error-message, .alert-error, [role='alert'][class*='error']")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more dashboard-specific tests as needed
# async def test_dashboard_stats():
# async def test_dashboard_quick_actions():
