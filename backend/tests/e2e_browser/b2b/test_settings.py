"""Settings Page E2E Tests"""
import pytest
import asyncio
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_settings_page_loads(authenticated_b2b_page: Page, b2b_test_setup):
    """Verify settings page loads successfully"""
    page = authenticated_b2b_page
    base_url = page.url.split('/dashboard')[0] if '/dashboard' in page.url else page.url.rstrip('/')
    
    # Navigate to settings
    await page.goto(f"{base_url}/settings")
    await page.wait_for_load_state("domcontentloaded")
    
    # Verify page loaded
    assert "/settings" in page.url
    
    # Has main content (heading or form)
    await expect(page.locator("h1, h2, form")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more settings tests as needed
# async def test_update_org_settings():
# async def test_sso_configuration():
