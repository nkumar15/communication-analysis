import pytest
import os
from playwright.async_api import Page
from tests.e2e_browser.pages.b2b.settings_page import SettingsPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_update_org_name(authenticated_b2b_page: Page):
    """Test updating organization name"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    settings_page = SettingsPage(authenticated_b2b_page, base_url)
    
    await settings_page.navigate()
    await settings_page.verify_loaded()
    
    await settings_page.update_org_name("Updated Test Company")
    await settings_page.verify_success_message()
    
    await settings_page.reload()
    await settings_page.verify_org_name_persisted("Updated Test Company")

@pytest.mark.browser
@pytest.mark.asyncio
async def test_sso_config_ui(authenticated_b2b_page: Page):
    """Test SSO configuration UI state"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    settings_page = SettingsPage(authenticated_b2b_page, base_url)
    
    await settings_page.navigate()
    await settings_page.verify_sso_config_visible()
