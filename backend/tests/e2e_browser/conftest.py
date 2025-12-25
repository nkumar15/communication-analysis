import pytest
import pytest_asyncio
import os
import asyncio
from playwright.async_api import Page
from uuid import uuid4

# Use the frontend URL from environment or default to localhost:3000
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context arguments.
    Set viewport size and base URL.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "base_url": FRONTEND_URL,
        "ignore_https_errors": True,
    }


# ============================================================================
# Browser Test Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def async_page(request):
    """
    Async Playwright page fixture for B2B tests.
    Creates a new browser context and page for each test.
    Respects HEADED env var and --headed CLI flag.
    SLOW env var controls slow_mo.
    """
    from playwright.async_api import async_playwright
    
    
    # Read environment variables for headed mode and slow motion
    # Respect both env var AND the standard --headed pytest flag
    try:
        cli_headed = request.config.getoption("--headed")
    except (ValueError, AttributeError):
        cli_headed = False
        
    headed = (os.getenv("HEADED") == "1") or cli_headed
    slow_mo = 5000 if os.getenv("SLOW") == "1" else 0
    
    # Wait for frontend to be ready (Critical for Docker CI)
    import httpx
    import time
    
    async def wait_for_server(url: str, timeout: int = 60):
        print(f"Waiting for {url} to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"Server {url} is ready!")
                        return True
            except Exception:
                await asyncio.sleep(1)
        raise TimeoutError(f"Server {url} did not become ready in {timeout} seconds")

    # Only wait if we are in Docker (checking FRONTEND_URL distinct from default)
    # or just always wait to be safe.
    try:
        await wait_for_server(FRONTEND_URL, timeout=45)
    except TimeoutError:
        print(f"WARNING: Frontend at {FRONTEND_URL} might not be ready. Proceeding anyway...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=not headed,
            slow_mo=slow_mo
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        yield page
        
        await page.close()
        await context.close()
        await browser.close()

@pytest_asyncio.fixture
async def authenticated_b2b_page(async_page: Page, b2b_test_setup):
    """
    Fixture that provides an authenticated Async Playwright page for B2B.
    Uses mock JWT backdoor for fast, reliable testing without Firebase network calls.
    """
    from .pages.b2b.login_page import LoginPage
    
    # Allow overriding base URL for Docker environments
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Enable console logging for debugging
    async_page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    async_page.on("pageerror", lambda exc: print(f"BROWSER ERROR: {exc}"))

    # Get the mock JWT token from the test setup
    # CRITICAL: Commit test data so backend API (separate process) can see it
    session = b2b_test_setup["session"]._session
    await session.commit()

    mock_jwt = b2b_test_setup["token"]
    
    # Use LoginPage POM
    login_page = LoginPage(async_page, base_url)
    await login_page.navigate()
    # Clear any previous auth state from browser
    await async_page.context.clear_cookies()
    await async_page.evaluate("() => { sessionStorage.clear(); localStorage.clear(); }")
    
    # Use the POM's mock JWT login method (no Firebase network calls)
    await login_page.login_with_mock_jwt(mock_jwt)
    
    # Verify we're no longer on login page
    if "/login" in async_page.url:
        # Still on login page - auth failed
        error_msg = ""
        if await async_page.locator(".error-message").count() > 0:
            error_msg = await async_page.locator('.error-message').text_content()
        
        pytest.fail(f"Failed to redirect to dashboard after mock JWT injection. Current URL: {async_page.url}. Error: {error_msg}")
        
    return async_page


# ============================================================================
# B2C Test Fixtures (Browser E2E) - Simplified for Smoke Tests
# ============================================================================

@pytest_asyncio.fixture
async def authenticated_b2c_page(async_page):
    """
    Simplified B2C fixture - just inject mock JWT for page access tests.
    No database setup needed for basic smoke tests.
    """
    # Import from parent conftest
    from ..conftest import encode_mock_jwt, create_mock_firebase_token
    
    base_url = os.getenv("FRONTEND_URL_B2C", "http://localhost:3001")
    
    # Wait for B2C frontend to be ready
    import httpx
    import time
    
    async def wait_for_server(url: str, timeout: int = 60):
        print(f"Waiting for {url} to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        print(f"Server {url} is ready!")
                        return True
            except Exception:
                await asyncio.sleep(1)
        raise TimeoutError(f"Server {url} did not become ready in {timeout} seconds")
    
    try:
        await wait_for_server(base_url, timeout=45)
    except TimeoutError:
        print(f"WARNING: Frontend at {base_url} might not be ready. Proceeding anyway...")
    
    # Navigate to B2C app FIRST (can't clear storage on about:blank)
    await async_page.goto(base_url)
    
    # Clear browser state
    await async_page.context.clear_cookies()
    await async_page.evaluate("() => { sessionStorage.clear(); localStorage.clear(); }")
    
    # Create a simple mock JWT (doesn't need real user in DB for page load tests)
    mock_jwt = encode_mock_jwt(create_mock_firebase_token(
        uid=f"b2c-smoke-{uuid4().hex[:8]}",
        email=f"b2c-smoke-{uuid4().hex[:8]}@example.com"
    ))
    
    # Inject mock JWT
    await async_page.evaluate(f"""
        () => {{
            sessionStorage.setItem('firebaseToken', '{mock_jwt}');
        }}
    """)
    
    # Navigate to dashboard to pick up auth
    await async_page.goto(base_url)
    await async_page.wait_for_load_state("domcontentloaded")
    
    return async_page



# ============================================================================
# Platform Test Fixtures (Browser E2E) - Simplified for Smoke Tests
# ============================================================================

@pytest_asyncio.fixture
async def authenticated_platform_page(async_page):
    """
    Simplified Platform fixture - just inject mock JWT for page access tests.
    Platform admin role for accessing super-admin pages.
    """
    # Import from parent conftest
    from ..conftest import encode_mock_jwt, create_mock_firebase_token
    
    base_url = os.getenv("FRONTEND_URL_PLATFORM", "http://localhost:3002")
    
    # Navigate to Platform app FIRST
    await async_page.goto(base_url)
    
    # Clear browser state
    await async_page.context.clear_cookies()
    await async_page.evaluate("() => { sessionStorage.clear(); localStorage.clear(); }")
    
    # Create mock JWT for platform admin
    mock_jwt = encode_mock_jwt(create_mock_firebase_token(
        uid="platform-admin-smoke",
        email="admin@platform.local"
    ))
    
    # Inject mock JWT
    await async_page.evaluate(f"""
        () => {{
            sessionStorage.setItem('firebaseToken', '{mock_jwt}');
        }}
    """)
    
    # Reload to pick up auth
    await async_page.reload()
    await async_page.wait_for_load_state("domcontentloaded")
    
    return async_page
