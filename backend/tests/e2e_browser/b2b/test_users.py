import pytest
import os
from playwright.async_api import Page
from tests.e2e_browser.pages.b2b.users_page import UsersPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_user_list_load(authenticated_b2b_page: Page):
    """Test that users list loads correctly"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    users_page = UsersPage(authenticated_b2b_page, base_url)
    
    await users_page.navigate()
    await users_page.verify_loaded()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_invite_user_flow(authenticated_b2b_page: Page):
    """Test opening invite modal and sending invite"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    users_page = UsersPage(authenticated_b2b_page, base_url)
    
    await users_page.navigate()
    
    test_email = "test-invite@example.com"
    await users_page.invite_user(test_email)
    await users_page.verify_invitation_sent(test_email)
