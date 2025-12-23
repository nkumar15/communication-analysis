"""Teams Page E2E Tests"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_teams_page_loads(authenticated_b2b_page: Page, b2b_test_setup):
    """Verify teams page loads successfully"""
    page = authenticated_b2b_page
    base_url = page.url.split('/dashboard')[0] if '/dashboard' in page.url else page.url.rstrip('/')
    
    # Navigate to teams
    await page.goto(f"{base_url}/teams")
    await page.wait_for_load_state("domcontentloaded")
    
    # Verify page loaded
    assert "/teams" in page.url
    
    # Has main heading
    await expect(page.locator("h1, h2")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more team management tests as needed
# async def test_create_team():
# async def test_team_list_displays():
