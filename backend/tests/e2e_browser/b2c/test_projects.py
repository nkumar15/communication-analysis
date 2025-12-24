"""Projects Page E2E Tests for B2C"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_projects_page_loads(authenticated_b2c_page: Page):
    """Verify projects page loads"""
    page = authenticated_b2c_page
    base_url = page.url.rstrip('/')
    
    # Navigate to projects
    await page.goto(f"{base_url}/projects")
    await page.wait_for_load_state("domcontentloaded")
    
    # Has main heading
    await expect(page.locator("h1, h2")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add project management tests
# async def test_create_project():
# async def test_project_list():
