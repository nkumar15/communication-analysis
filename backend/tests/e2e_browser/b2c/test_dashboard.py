"""Dashboard/Workspace E2E Tests for B2C"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_dashboard_loads(authenticated_b2c_page: Page):
    """Verify B2C dashboard/workspace page loads"""
    page = authenticated_b2c_page
    
    # Verify not on login page
    assert "/login" not in page.url and "/signup" not in page.url
    
    # Page has main content
    await expect(page.locator("h1, h2, [data-testid='workspace']")).to_be_visible(timeout=5000)
    
    # No error messages
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more tests as needed
# async def test_workspace_switching():
# async def test_create_workspace():
