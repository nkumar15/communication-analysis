from playwright.async_api import Page, expect
from ..async_base_page import AsyncBasePage

class LoginPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str = "http://localhost:3000"):
        super().__init__(page)
        self.base_url = base_url
        self.path = "/login"

    async def navigate(self):
        await self.page.goto(f"{self.base_url}{self.path}")

    async def verify_on_login_page(self):
        # Wait for page navigation to complete
        await self.page.wait_for_load_state("domcontentloaded")
        # Wait for the h1 to be attached to the DOM (not necessarily visible yet)
        h1_locator = self.page.locator("h1")
        await h1_locator.wait_for(state="attached", timeout=10000)
        await expect(h1_locator).to_contain_text("Enterprise SSO Portal")
    
    async def login_with_mock_jwt(self, mock_jwt: str):
        """
        Injects mock JWT via localStorage for E2E testing (no Firebase network calls).
        This is the fastest auth method for tests.
        """
        # Enable console logging to debug auth issues
        self.page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
        
        print(f"🔑 Injecting mock JWT via sessionStorage and navigating...")
        # Store in sessionStorage where the auth service/App looks for it
        await self.page.evaluate(f"sessionStorage.setItem('firebaseToken', '{mock_jwt}')")
        
        # Navigate directly to dashboard
        await self.page.goto(f"{self.base_url}/dashboard")
        
        # Wait for dashboard to load
        try:
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            print(f"✅ Navigated to dashboard: {self.page.url}")
        except Exception as e:
            print(f"⚠️ Dashboard load failed after 5s: {e}")
            print(f"❌ Current URL: {self.page.url}")
            
            # Check for error messages or redirects
            if "/login" in self.page.url:
                print(f"❌ Redirected back to login - auth failed")
            
            raise Exception(f"Dashboard navigation failed. URL: {self.page.url}")
    
    async def login_with_custom_token(self, custom_token: str):
        """
        Injects custom token via localStorage and reloads to trigger auto-login.
        NOTE: This requires Firebase network access - use login_with_mock_jwt for tests instead.
        """
        # Enable console logging to debug auth issues
        self.page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))
        
        print(f"🔑 Injecting custom token via localStorage...")
        await self.page.evaluate(f"localStorage.setItem('custom_token', '{custom_token}')")
        
        # Reload and wait for navigation to complete (should navigate to dashboard)
        await self.page.reload()
        
        # Wait for the custom token login flow to complete
        # The page will auto-login and navigate away from /login
        # Use shorter timeout to  fail fast
        try:
            await self.page.wait_for_url(lambda url: "/login" not in url, timeout=5000)
            print(f"✅ Auto-login completed, navigated to: {self.page.url}")
        except Exception as e:
            print(f"⚠️ Navigation wait failed after 5s: {e}")
            print(f"❌ Current URL: {self.page.url}")
            
            # Check for error messages on page
            if await self.page.locator(".error-message").count() > 0:
                error_text = await self.page.locator(".error-message").text_content()
                print(f"❌ Error on page: {error_text}")
            
            raise Exception(f"Auth flow failed - still on login page after 5s. URL: {self.page.url}")
    
    async def verify_login_error(self, error_text: str):
        error_msg = self.page.locator(".error-message")
        await expect(error_msg).to_be_visible()
        await expect(error_msg).to_contain_text(error_text)
