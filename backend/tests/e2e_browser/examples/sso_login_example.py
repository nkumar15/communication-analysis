"""Example: How to use the SSO login method"""
import pytest
from playwright.async_api import Page
import os

# This is an EXAMPLE - not meant to run as-is
# Shows how to use login_with_sso() in your tests

@pytest.mark.asyncio
@pytest.mark.browser
async def test_sso_login_example(async_page: Page):
    """
    Example: Test using real SSO login flow
    
    NOTE: This requires:
    1. Owner user to exist in database (owner@firstcompany.net)
    2. SSO provider configured for that tenant
    3. Valid credentials
    """
    from pages.b2b.login_page import LoginPage
    
    # Get credentials from environment
    email = os.getenv("B2B_OWNER_EMAIL", "owner@firstcompany.net")
    password = os.getenv("B2B_OWNER_PASSWORD", "owner01-pwd")
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Create login page instance
    login_page = LoginPage(async_page, base_url)
    
    # Perform SSO login (handles popup automatically)
    await login_page.login_with_sso(email, password)
    
    # Verify we're on dashboard
    assert "/dashboard" in async_page.url
    print("✅ SSO login successful!")


@pytest.mark.asyncio
@pytest.mark.browser  
async def test_teams_with_sso_login(async_page: Page):
    """
    Example: Navigate to teams page after SSO login
    """
    from pages.b2b.login_page import LoginPage
    from pages.b2b.teams_page import TeamsPage
    
    email = os.getenv("B2B_OWNER_EMAIL", "owner@firstcompany.net")
    password = os.getenv("B2B_OWNER_PASSWORD", "owner01-pwd")
    
    # Login with SSO
    login_page = LoginPage(async_page)
    await login_page.login_with_sso(email, password)
    
    # Navigate to teams
    teams_page = TeamsPage(async_page)
    await teams_page.navigate()
    
    # Your test assertions here
    assert "/teams" in async_page.url


# ============================================================================
# Option: Update fixture to use SSO login instead of mock JWT
# ============================================================================

# If you want to use REAL SSO for all tests, update conftest.py:
#
# @pytest_asyncio.fixture
# async def authenticated_b2b_page_sso(async_page, b2b_test_setup):
#     """
#     Alternative fixture using REAL SSO login (slower but tests actual flow)
#     """
#     from .pages.b2b.login_page import LoginPage
#     
#     email = os.getenv("B2B_OWNER_EMAIL", "owner@firstcompany.net")
#     password = os.getenv("B2B_OWNER_PASSWORD", "owner01-pwd") 
#     base_url = os.getenv("BASE_URL", "http://localhost:3000")
#     
#     login_page = LoginPage(async_page, base_url)
#     await login_page.login_with_sso(email, password)
#     
#     return async_page
#
# Then use in tests:
# async def test_something(authenticated_b2b_page_sso: Page):
#     page = authenticated_b2b_page_sso
#     # ... your test code
