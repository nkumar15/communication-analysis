import pytest
import os
from playwright.async_api import Page
from tests.e2e_browser.pages.b2b.billing_page import BillingPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_billing_page_load(authenticated_b2b_page: Page):
    """Test billing page loads and shows current plan"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    billing_page = BillingPage(authenticated_b2b_page, base_url)
    
    await billing_page.navigate_subscription()
    await billing_page.verify_subscription_loaded()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_billing_profile_update(authenticated_b2b_page: Page):
    """Test updating billing profile (Tax ID)"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    billing_page = BillingPage(authenticated_b2b_page, base_url)
    
    await billing_page.navigate_subscription()
    
    tax_id = "US-123456789"
    await billing_page.update_billing_profile(tax_id)
    
    await billing_page.reload()
    await billing_page.verify_billing_profile_persisted(tax_id)

@pytest.mark.browser
@pytest.mark.asyncio
async def test_upgrade_flow_ui(authenticated_b2b_page: Page):
    """Test that upgrade dialog opens"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    billing_page = BillingPage(authenticated_b2b_page, base_url)
    
    await billing_page.navigate_subscription()
    await billing_page.verify_upgrade_dialog()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_invoices_page(authenticated_b2b_page: Page):
    """Test that the Invoices page loads"""
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    billing_page = BillingPage(authenticated_b2b_page, base_url)
    
    await billing_page.navigate_invoices()
    await billing_page.verify_invoices_loaded()
