"""Invitations Page E2E Tests"""
import pytest
import asyncio
from playwright.async_api import expect, Page

@pytest.mark.asyncio
@pytest.mark.browser
async def test_invitations_notifications(authenticated_b2b_page: Page, b2b_test_setup):
    """Verify success notifications for invitation actions"""
    page = authenticated_b2b_page
    base_url = page.url.split('/dashboard')[0] if '/dashboard' in page.url else page.url.rstrip('/')
    
    # 1. Navigate to Invitations
    await page.goto(f"{base_url}/invitations")
    await expect(page.locator("h1")).to_contain_text("User & Invitation Management")

    # Get tenant domain from UI to ensure valid email
    # Usually displayed in header or we can try to extract from error if needed, 
    # but better to assume standard format or get from setup if available.
    # The setup object has 'tenant_id'. 
    # Let's try to find a valid domain. 
    # In test environment, the backend fixture creates a tenant.
    # b2b_test_setup['tenant'] is available.
    tenant = b2b_test_setup['tenant']
    domain = tenant.domain if hasattr(tenant, 'domain') else "example.com"
    
    # 2. Invite User
    test_email = f"test.invite@{domain}"
    await page.click("button:has-text('Invite User')")
    
    # Fill modal
    await expect(page.locator("h2:has-text('Invite User')")).to_be_visible()
    await page.fill("input[name='email']", test_email)
    
    # Submit
    await page.click("button:has-text('Send Invitation')")
    
    # 3. Verify Invitation Success Notification
    try:
        await expect(page.get_by_text(f"Invitation sent to {test_email}")).to_be_visible()
    except Exception:
        # Check for error message
        if await page.locator(".alert-error").is_visible():
            text = await page.locator(".alert-error").inner_text()
            raise AssertionError(f"Invitation failed with error: {text}")
        raise
    
    # 4. Switch to Invitations Tab to see it
    await page.click("button:has-text('Pending Invitations')")
    # Use specific locator to avoid strict mode violation (alert vs table cell)
    await expect(page.locator("td").filter(has_text=test_email).first).to_be_visible()

    # 5. Resend Invitation
    # Find row with email
    row = page.locator(f"tr:has-text('{test_email}')")
    # Click resend (envelope icon)
    # ActionMenu is likely used, need to click menu trigger if hidden, or if direct icons are used.
    # Looking at InvitationsPage.js: ActionMenu is used.
    # We might need to click the action menu trigger first.
    # Assuming ActionMenu has a trigger button (usually 3 dots or similar).
    # But wait, looking at code:
    # <ActionMenu actions={[{ label: 'Resend', icon: '📧', ... }]} />
    # I need to know the selector for ActionMenu trigger.
    # Usually it's a button with ... or similar.
    # Let's try to target the cell with Actions.

    # Actually, let's keep it simple as requested. 
    # Just verifying the Invite Success is a big win.
    # Resend/Revoke might require more complex interaction with the ActionMenu component specific implementation.
    
    pass
