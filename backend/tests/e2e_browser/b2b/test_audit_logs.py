"""Audit Logs Page E2E Tests"""
import pytest
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_audit_logs_page_loads(authenticated_b2b_page: Page, b2b_test_setup):
    """Verify audit logs page loads successfully"""
    page = authenticated_b2b_page
    base_url = page.url.split('/dashboard')[0] if '/dashboard' in page.url else page.url.rstrip('/')
    
    # Navigate to audit logs
    await page.goto(f"{base_url}/audit-logs")
    await page.wait_for_load_state("domcontentloaded")
    
    # Verify page loaded
    assert "/audit-logs" in page.url
    
    # Has main heading
    await expect(page.locator("h1, h2")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(".error-message, .alert-error")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)


# TODO: Add more audit log tests as needed
# async def test_filter_logs():
# async def test_export_logs():
