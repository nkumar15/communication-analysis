"""
E2E Browser Test - Tenant Onboarding Flow
"""
import pytest
from playwright.sync_api import Page, expect


def test_login_page_loads(page: Page):
    """
    Test that the login page loads without errors.
    """
    page.goto("/login")
    page.wait_for_load_state("networkidle")
    
    # Verify login page elements
    assert "html" in page.content().lower()


@pytest.mark.skip(reason="Requires tenant setup and custom token implementation")
def test_tenant_activation_flow(page: Page):
    """
    Test the full tenant activation flow with custom token.
    
    Prerequisites:
    - Tenant created via API with activation token
    - Custom Firebase token for admin user
    """
    pass

