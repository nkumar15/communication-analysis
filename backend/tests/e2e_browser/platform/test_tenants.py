"""Tenants Page E2E Tests for Platform"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_tenants_page_loads(authenticated_platform_page: Page):
    """Verify Platform tenants page loads"""
    page = authenticated_platform_page
    base_url = page.url.rstrip('/')
    
    # Navigate to tenants
    await page.goto(f"{base_url}/super-admin/tenants")
    await page.wait_for_load_state("domcontentloaded")
    
    # Has main heading
    await expect(page.locator("h1, h2")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add tenant management tests
# async def test_create_tenant():
