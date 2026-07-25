"""Dashboard E2E Tests for Platform"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_dashboard_loads(authenticated_platform_page: Page):
    """Verify Platform dashboard loads"""
    page = authenticated_platform_page
    
    # Verify not on login page
    assert "/login" not in page.url
    
    # Page has main content
    await expect(page.locator("h1, h2")).to_be_visible(timeout=5000)
    
    # No error messages
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more dashboard tests as needed
