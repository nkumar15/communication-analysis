"""Settings Page E2E Tests for B2C"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_settings_page_loads(authenticated_b2c_page: Page):
    """Verify settings page loads"""
    page = authenticated_b2c_page
    base_url = page.url.rstrip('/')
    
    # Navigate to settings
    await page.goto(f"{base_url}/settings")
    await page.wait_for_load_state("domcontentloaded")
    
    # Has main content (use .first() since multiple h1/h2/form elements exist)
    await expect(page.locator("h1, h2, form").first).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add settings tests
# async def test_update_profile():
# async def test_change_password():
