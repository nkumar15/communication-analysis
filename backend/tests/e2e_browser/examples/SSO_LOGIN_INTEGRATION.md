# SSO Login Integration Guide

## Overview

The `login_with_sso()` method has been added to `LoginPage` to support **real SSO popup authentication**.

## Location

**File:** `backend/tests/e2e_browser/pages/b2b/login_page.py`

**Method:** `login_with_sso(email: str, password: str)`

## What It Does

1. ✅ Navigates to login page
2. ✅ Fills email address
3. ✅ Clicks "Continue with SSO →" button
4. ✅ **Handles popup window** automatically
5. ✅ Fills password in popup
6. ✅ Clicks Continue
7. ✅ Waits for popup to close
8. ✅ Verifies redirect to dashboard

## Usage

### Option 1: Use in Individual Tests

```python
from pages.b2b.login_page import LoginPage

@pytest.mark.asyncio
@pytest.mark.browser
async def test_my_feature(async_page: Page):
    # Login with SSO
    login_page = LoginPage(async_page, "http://localhost:3000")
    await login_page.login_with_sso(
        email="owner@firstcompany.net",
        password="owner01-pwd"
    )
    
    # Now you're on dashboard, continue testing
    assert "/dashboard" in async_page.url
```

### Option 2: Create SSO Fixture (Optional)

Add to `backend/tests/e2e_browser/conftest.py`:

```python
@pytest_asyncio.fixture
async def authenticated_b2b_page_sso(async_page):
    """
    Alternative B2B fixture using REAL SSO login.
    Slower than mock JWT but tests actual user flow.
    """
    from .pages.b2b.login_page import LoginPage
    import os
    
    email = os.getenv("B2B_OWNER_EMAIL", "owner@firstcompany.net")
    password = os.getenv("B2B_OWNER_PASSWORD", "owner01-pwd")
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    login_page = LoginPage(async_page, base_url)
    await login_page.login_with_sso(email, password)
    
    return async_page
```

Then use in tests:

```python
async def test_something(authenticated_b2b_page_sso: Page):
    page = authenticated_b2b_page_sso
    # Already logged in via SSO
    assert "/dashboard" in page.url
```

## Current vs SSO Login

### Current: Mock JWT (Fast)
- **Speed:** ~2 seconds
- **Method:** `login_with_mock_jwt()`
- **Use case:** Fast development/testing
- **Fixture:** `authenticated_b2b_page`

### New: Real SSO (Complete)
- **Speed:** ~5-8 seconds (popup + auth)
- **Method:** `login_with_sso()`
- **Use case:** E2E testing of actual SSO flow
- **Fixture:** Create `authenticated_b2b_page_sso` (optional)

## Recommendation

**Keep both approaches:**
- Use **mock JWT** for most tests (faster development)
- Use **real SSO** for critical E2E tests (actual user flow)

## Environment Variables

```bash
export B2B_OWNER_EMAIL="owner@firstcompany.net"
export B2B_OWNER_PASSWORD="owner01-pwd"
export BASE_URL="http://localhost:3000"
```

## Example: Full Test

```python
import pytest
from playwright.async_api import Page
from pages.b2b.login_page import LoginPage
from pages.b2b.teams_page import TeamsPage

@pytest.mark.asyncio
@pytest.mark.browser
async def test_create_team_with_sso(async_page: Page):
    """Test creating a team using real SSO login"""
    
    # 1. Login with SSO
    login_page = LoginPage(async_page, "http://localhost:3000")
    await login_page.login_with_sso(
        email="owner@firstcompany.net",
        password="owner01-pwd"
    )
    
    # 2. Navigate to teams
    teams_page = TeamsPage(async_page)
    await teams_page.navigate()
    
    # 3. Create team (your test logic here)
    # await teams_page.create_team("Engineering")
    # ...
```

## Troubleshooting

**Popup doesn't appear:**
- Check that SSO provider is configured for the tenant
- Verify "Continue with SSO →" button exists on page

**Password field not found:**
- Check popup URL to ensure it's the expected SSO page
- SSO provider may use different field names

**Timeout waiting for popup to close:**
- Credentials may be incorrect
- SSO provider may be showing an error
- Add `--headed` flag to see what's happening visually
