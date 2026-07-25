from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class BillingPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.subscription_path = "/billing/subscription"
        self.invoices_path = "/b2b/billing/invoices"

    async def navigate_subscription(self):
        await self.page.goto(f"{self.base_url}{self.subscription_path}")
    
    async def navigate_invoices(self):
        await self.page.goto(f"{self.base_url}{self.invoices_path}")

    async def verify_subscription_loaded(self):
        await expect(self.page.locator("h1")).to_contain_text("Subscription & Billing")
        await expect(self.page.locator("h3:has-text('Current Plan')")).to_be_visible()
        await expect(self.page.locator("text=Current Plan")).to_be_visible()

    async def update_billing_profile(self, tax_id: str):
        # Locate input robustly
        await self.page.locator("label:has-text('Tax ID / EIN')").locator("..").locator("input").fill(tax_id)
        await self.page.click("button:has-text('Save Details')")

    async def verify_billing_profile_persisted(self, tax_id: str):
        await expect(self.page.locator("label:has-text('Tax ID / EIN')").locator("..").locator("input")).to_have_value(tax_id)

    async def verify_upgrade_dialog(self):
        upgrade_btn = self.page.locator("button:has-text('Upgrade to')").first
        
        if await upgrade_btn.count() > 0 and await upgrade_btn.is_visible():
            await upgrade_btn.click()
            await expect(self.page.locator("h2:has-text('Upgrade to')")).to_be_visible()
            await expect(self.page.locator("button:has-text('Monthly Billing')")).to_be_visible()
            # Close
            await self.page.locator("button:has-text('Cancel')").click()
            await expect(self.page.locator("h2:has-text('Upgrade to')")).not_to_be_visible()

    async def verify_invoices_loaded(self):
        await expect(self.page.locator("text=Invoices").first).to_be_visible()
        await expect(self.page.locator("button:has-text('Refresh')")).to_be_visible()
        # Look for table or empty state
        await expect(self.page.locator("text=No invoices yet").or_(self.page.locator("text=Invoice Number"))).to_be_visible()
