from playwright.async_api import Page
import pytest
import os
from tests.e2e_browser.pages.b2b.audit_logs_page import AuditLogsPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_audit_logs_load(authenticated_b2b_page: Page):
    """
    Test that the Audit Logs page loads and displays logs.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    audit_page = AuditLogsPage(authenticated_b2b_page, base_url)
    
    await audit_page.navigate()
    await audit_page.verify_loaded()
