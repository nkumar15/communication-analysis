import pytest
import os
from playwright.async_api import Page, expect
from tests.e2e_browser.pages.b2b.dashboard_page import DashboardPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_dashboard_stats_load(authenticated_b2b_page: Page):
    """
    Test that the admin dashboard loads stats correctly.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    dashboard_page = DashboardPage(authenticated_b2b_page, base_url)
    
    # 1. Verify Welcome Message
    await dashboard_page.verify_loaded()
    
    # 2. Verify Stats Cards
    await dashboard_page.verify_stats_cards(4)
    
    # 3. Verify Activity Feed
    await dashboard_page.verify_recent_activity()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_dashboard_navigation(authenticated_b2b_page: Page):
    """Test navigation from dashboard shortcuts"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    dashboard_page = DashboardPage(authenticated_b2b_page, base_url)
    
    # Click "Manage Users" shortcut
    await dashboard_page.navigate_to_users()
