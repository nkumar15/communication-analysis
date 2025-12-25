"""Dashboard E2E Tests"""
import pytest
import asyncio
from playwright.async_api import expect, Page


@pytest.mark.asyncio
@pytest.mark.browser
async def test_dashboard_interaction(authenticated_b2b_page: Page):
    """
    Test Dashboard interaction using fast Mock JWT auth.
    (Converted from recording, but optimized to skip full login flow)
    
    1. Fast Login (via fixture)
    2. Click Dashboard Heading (from recording)
    """
    from ..pages.b2b.dashboard_page import DashboardPage

    page = authenticated_b2b_page
    dashboard_page = DashboardPage(page)
    
    # Verify interactive elements from recording
    await dashboard_page.verify_heading_interactive()
