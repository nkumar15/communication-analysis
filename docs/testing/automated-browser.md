# Automated Browser Testing (E2E)

## Overview

**Status**: ✅ Production-Ready Baseline (16/16 tests passing, 100%)

Our End-to-End (E2E) browser tests verify complete user workflows across all three portals using Playwright. Tests run in Docker containers with frontend services automatically managed via Docker Compose profiles.

### Test Results

| Portal | Tests | Status | Time |
|--------|-------|--------|------|
| B2B    | 8     | ✅ 100% | 40s  |
| B2C    | 5     | ✅ 100% | 14s  |
| Platform | 3   | ✅ 100% | 12s  |
| **Total** | **16** | **✅ 100%** | **66s** |

## Current Approach

### Philosophy: Simple Smoke Tests

Instead of complex CRUD tests with brittle assertions, we use **simple page load tests** as a reliable baseline:

**What We Test:**
- ✅ Page loads without errors
- ✅ Authentication works
- ✅ Main content visible
- ✅ No error messages displayed

**What We Don't Test (Yet):**
- ❌ Complex workflows (Create/Update/Delete)
- ❌ Specific UI text (brittle)
- ❌ Form interactions
- ❌ Multi-step processes

### Architecture

```
frontend/ (Docker, E2E only)         backend/ (Docker)
┌──────────────────────┐            ┌─────────────────┐
│ frontend-b2b:3000    │────API────▶│ b2b-api:8000    │
│ frontend-b2c:3001    │────calls──▶│ b2c-api:8002    │
│ frontend-platform:3002│           │ platform-api:8001│
└──────────────────────┘            └─────────────────┘
         ▲                                    ▲
         │                                    │
    Playwright                          Mock JWT Auth
    (in Docker)                         (No Firebase)
```

### Test Structure

**Page-Based Organization:**
```
tests/e2e_browser/
├── b2b/
│   ├── test_dashboard.py          # Dashboard smoke test
│   ├── test_users.py               # Users page smoke test
│   ├── test_teams.py               # Teams page smoke test
│   ├── test_roles.py               # Roles page smoke test
│   ├── test_team_roles.py          # Team roles smoke test
│   ├── test_settings.py            # Settings page smoke test
│   ├── test_billing.py             # Billing page smoke test
│   └── test_audit_logs.py          # Audit logs smoke test
├── b2c/
│   ├── test_dashboard.py           # Dashboard smoke test
│   ├── test_workspaces.py          # Workspaces smoke test
│   ├── test_projects.py            # Projects smoke test
│   ├── test_subscription.py        # Subscription smoke test
│   └── test_settings.py            # Settings smoke test
├── platform/
│   ├── test_dashboard.py           # Dashboard smoke test
│   ├── test_tenants.py             # Tenants smoke test
│   └── test_plans.py               # Plans smoke test
├── pages/                           # Page Object Models
│   ├── b2b/
│   │   ├── dashboard_page.py
│   │   ├── users_page.py
│   │   └── ...
│   ├── b2c/
│   │   ├── signup_page.py
│   │   └── ...
│   └── platform/
│       └── ...
└── conftest.py                      # Fixtures & helpers
```

### Test Template

Every test follows this simple pattern:

```python
import pytest
from playwright.async_api import expect, Page

@pytest.mark.asyncio
@pytest.mark.browser
async def test_page_loads(authenticated_portal_page: Page):
    \"\"\"Verify page loads successfully\"\"\"
    page = authenticated_portal_page
    base_url = page.url.rstrip('/')
    
    # Navigate to page
    await page.goto(f\"{base_url}/path\")
    await page.wait_for_load_state(\"domcontentloaded\")
    
    # Verify loaded
    assert \"/path\" in page.url
    
    # Has main heading
    await expect(page.locator(\"h1, h2\")).to_be_visible(timeout=5000)
    
    # No errors
    error_locator = page.locator(\".error-message, .alert-error\")
    if await error_locator.count() > 0:
        await expect(error_locator).to_have_count(0)
```

## Running Tests

### Quick Start

```bash
# Run all browser tests for a portal
make test-browser-b2b
make test-browser-b2c
make test-browser-platform

# Run specific test file
make test-browser-b2b TEST_PATH=tests/e2e_browser/b2b/test_dashboard.py

# Run with visible browser (headed mode)
make test-browser-b2b HEADED=1

# Run in slow motion (for debugging)
make test-browser-b2b HEADED=1 SLOW=1
```

### Behind the Scenes

When you run `make test-browser-b2b`:
1. Starts `frontend-b2b` container (Docker Compose with `e2e` profile)
2. Starts backend services if not running
3. Runs Playwright tests in `e2e-tests` container
4. Frontend container stays running for subsequent tests

## Authentication Strategy

### Mock JWT (No Firebase Network Calls)

E2E tests use **mock JWT tokens** instead of real Firebase authentication:

**Benefits:**
- ✅ Fast (no network calls)
- ✅ Reliable (no external dependencies)
- ✅ Isolated (no Firebase project needed)
- ✅ Flexible (can test any user/role instantly)

**How It Works:**

1. **Test Fixture** creates mock JWT with signature `mock_signature`
2. **Frontend E2E Backdoor** detects mock JWT and bypasses Firebase
3. **Backend API** validates mock JWT normally (same validation path)

### Frontend E2E Backdoors

Each portal has authentication bypass for E2E tests:

**B2B** (ProtectedRoute.js):
```javascript
// E2E Test Backdoor
const e2eToken = sessionStorage.getItem('firebaseToken');
if (e2eToken && e2eToken.includes('mock_signature')) {
    console.log('🧪 E2E: Bypassing auth check');
    setIsAuthenticated(true);
    return;
}
```

**B2C** (B2CApp.js):
```javascript
// E2E Test Backdoor in ProtectedRoute
const e2eToken = sessionStorage.getItem('firebaseToken');
if (e2eToken && e2eToken.includes('mock_signature')) {
    setIsAuthenticated(true);
    return () => {};
}
```

**Platform** (PlatformAdminRoute.js):
```javascript
// E2E Test Backdoor
const e2eToken = sessionStorage.getItem('firebaseToken');
if (e2eToken && e2eToken.includes('mock_signature')) {
    setIsAuthorized(true);
    setLoading(false);
    return;
}
```

### Test Fixtures

**conftest.py** provides auth fixtures for each portal:

```python
# B2B: Full database setup with tenant/user
@pytest_asyncio.fixture
async def authenticated_b2b_page(async_page, b2b_test_setup):
    # Creates tenant + user in DB
    # Commits data so backend API can see it
    # Injects mock JWT
    # Returns authenticated page
    
# B2C: Simplified (no DB needed for smoke tests)
@pytest_asyncio.fixture
async def authenticated_b2c_page(async_page):
    # Just injects mock JWT
    # No database setup
    
# Platform: Simplified
@pytest_asyncio.fixture
async def authenticated_platform_page(async_page):
    # Just injects mock JWT
    # Platform admin role assumed
```

## Key Architectural Decisions

### 1. Frontend Containers Only for E2E

**Problem:** Frontend Docker containers blocked ports during local development

**Solution:** Docker Compose profiles
```yaml
# docker-compose.yml
frontend-b2b:
  profiles: [\"e2e\"]  # Only starts for E2E tests
```

**Development Workflow:**
- `make dev-up` - Start backend only (ports free)
- `make test-browser-*` - Auto-starts frontends
- Run local frontends: `cd frontend && npm run dev:b2b`

### 2. Database Commits for B2B

**Problem:** API couldn't see test data (separate process)

**Solution:** Explicit commit in fixture
```python
# Backend API needs committed data
session = b2b_test_setup[\"session\"]
await session.commit()
```

### 3. Browser State Clearing

**Problem:** JWT from previous test leaked into next test

**Solution:** Clear between tests
```python
await async_page.goto(base_url)  # Navigate first!
await async_page.context.clear_cookies()
await async_page.evaluate(\"() => { 
    sessionStorage.clear(); 
    localStorage.clear(); 
}\")
```

## Best Practices

### DO ✅

1. **Keep Tests Simple**
   - One assertion: page loads
   - One assertion: no errors
   - Add complexity only when needed

2. **Use Fixtures**
   - Let fixtures handle auth
   - Don't repeat setup code

3. **Wait Properly**
   - `await page.wait_for_load_state(\"domcontentloaded\")`
   - Use timeouts: `expect(...).to_be_visible(timeout=5000)`

4. **Handle Multiple Elements**
   - Use `.first` if locator matches multiple: `page.locator(\"h1\").first`
   - Or be more specific: `page.locator(\"h1#page-title\")`

5. **Check Errors**
   - Always verify no error messages shown

### DON'T ❌

1. **Don't Test Specific Text**
   - ❌ `expect(page.locator(\"h1\")).to_contain_text(\"Dashboard Overview\")`
   - ✅ `expect(page.locator(\"h1\")).to_be_visible()`

2. **Don't Clear Before Navigate**
   - ❌ `clear_storage() then goto()` - SecurityError on about:blank
   - ✅ `goto() then clear_storage()`

3. **Don't Assume Auth State**
   - Always use fixtures
   - Don't manually inject tokens in tests

4. **Don't Skip Error Checks**
   - Always check for error messages
   - Page might load but show errors

## Expansion Roadmap

### Phase 1: Add Critical Workflows (Priority)

Expand tests for business-critical features:

**B2B:**
- `test_invite_user_flow()` - Complete user invitation
- `test_create_team()` - Team creation
- `test_subscription_upgrade()` - Billing flow

**B2C:**
- `test_signup_flow()` - Complete signup
- `test_create_workspace()` - Workspace creation
- `test_join_workspace()` - Invitation acceptance

**Platform:**
- `test_create_tenant()` - Tenant onboarding
- `test_activate_tenant()` - Activation flow

### Phase 2: Form Interactions

Test data entry and validation:

```python
async def test_user_invite_form():
    # Fill form
    await page.fill(\"[name='email']\", \"newuser@example.com\")
    await page.select_option(\"[name='role']\", \"admin\")
    
    # Submit
    await page.click(\"button[type='submit']\")
    
    # Verify success
    await expect(page.locator(\".success-message\")).to_be_visible()
    await expect(page.locator(\"td\")).to_contain_text(\"newuser@example.com\")
```

### Phase 3: Navigation Flows

Test multi-page workflows:

```python
async def test_project_task_workflow():
    # Create project
    await page.goto(f\"{base_url}/projects\")
    await page.click(\"text=New Project\")
    # ... create project
    
    # Navigate to project
    await page.click(f\"text={project_name}\")
    
    # Create task
    await page.click(\"text=New Task\")
    # ... create task
    
    # Verify in list
    await expect(page.locator(f\"text={task_name}\")).to_be_visible()
```

### Phase 4: Error Scenarios

Test validation and error handling:

```python
async def test_invite_validation():
    # Try invalid email
    await page.fill(\"[name='email']\", \"invalid-email\")
    await page.click(\"button[type='submit']\")
    
    # Verify error shown
    await expect(page.locator(\".error-message\")).to_contain_text(\"Invalid email\")
```

### Phase 5: Visual Regression

Add screenshot comparison:

```python
async def test_dashboard_visual():
    await page.goto(f\"{base_url}/dashboard\")
    
    # Take screenshot
    await page.screenshot(path=\"screenshots/dashboard.png\")
    
    # Compare with baseline (using Percy, Chromatic, or similar)
```

## Advanced Patterns

### Page Object Models

For complex interactions, use Page Objects:

```python
# pages/b2b/users_page.py
class UsersPage(AsyncBasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page)
        self.base_url = base_url
        
    async def navigate(self):
        await self.page.goto(f\"{self.base_url}/users\")
        
    async def invite_user(self, email: str, role: str):
        await self.page.click(\"button:has-text('Invite User')\")
        await self.page.fill(\"[name='email']\", email)
        await self.page.select_option(\"[name='role']\", role)
        await self.page.click(\"button[type='submit']\")
        
    async def get_user_row(self, email: str):
        return self.page.locator(f\"tr:has-text('{email}')\")

# test_users.py
async def test_invite_user(authenticated_b2b_page):
    users_page = UsersPage(authenticated_b2b_page, base_url)
    await users_page.navigate()
    await users_page.invite_user(\"test@example.com\", \"admin\")
    
    row = await users_page.get_user_row(\"test@example.com\")
    await expect(row).to_be_visible()
```

### Data-Driven Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize(\"role,expected_access\", [
    (\"admin\", True),
    (\"member\", True),
    (\"viewer\", False),
])
async def test_page_access_by_role(authenticated_b2b_page, role, expected_access):
    # Create user with specific role
    # Try to access page
    # Verify access granted/denied
```

### Network Mocking

Mock API responses:

```python
async def test_with_api_mock(authenticated_b2b_page):
    # Mock API response
    await authenticated_b2b_page.route(
        \"**/api/users\",
        lambda route: route.fulfill(
            status=200,
            body=json.dumps([{\"id\": 1, \"email\": \"test@example.com\"}])
        )
    )
    
    await authenticated_b2b_page.goto(f\"{base_url}/users\")
    # Page will use mocked API response
```

## Troubleshooting

### Common Issues

**Tests Stuck on Login Page**
- Check if E2E backdoor is present in frontend
- Verify mock JWT has `mock_signature`
- Check browser console for auth errors

**SecurityError: SessionStorage Access Denied**
- Navigate to URL before clearing storage
- Don't clear on `about:blank`

**Strict Mode Violation (Multiple Elements)**
- Use `.first`: `page.locator(\"h1\").first`
- Or be more specific with selectors

**CORS Errors**
- Check `cors_origins` includes Docker frontend URLs
- Verify `REACT_APP_API_URL` is set correctly

**Frontend Container Not Starting**
- Check Docker Compose profiles: `docker-compose --profile e2e ps`
- Manually start: `docker-compose --profile e2e up -d frontend-b2b`

### Debug Commands

```bash
# Run with browser visible
make test-browser-b2b HEADED=1

# Run in slow motion
make test-browser-b2b HEADED=1 SLOW=1

# Check frontend logs
docker logs sso_frontend_b2b

# Check if frontend is running
docker ps | grep frontend

# Start frontend manually
docker-compose --profile e2e up -d frontend-b2b
```

## Performance Optimization

### Current Performance

- B2B: ~5s per test
- B2C: ~3s per test  
- Platform: ~4s per test

### Optimization Strategies

1. **Parallel Execution**
   ```bash
   pytest tests/e2e_browser/b2b/ -n 4  # 4 workers
   ```

2. **Selective Testing**
   - Run smoke tests in CI (fast feedback)
   - Run full suite nightly

3. **Reuse Browser Context**
   - Keep browser open between tests
   - Clear state instead of restart

4. **Skip Animations**
   ```javascript
   // Disable CSS animations
   await page.addStyleTag({ content: '* { animation: none !important; }' })
   ```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: |
          make dev-up
          sleep 10
      
      - name: Run B2B tests
        run: make test-browser-b2b
      
      - name: Run B2C tests
        run: make test-browser-b2c
      
      - name: Run Platform tests
        run: make test-browser-platform
      
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-screenshots
          path: screenshots/
```

## Metrics & Monitoring

### Track These Metrics

1. **Pass Rate**: Target 100%
2. **Execution Time**: < 2 minutes total
3. **Flakiness**: < 1% retry rate
4. **Coverage**: Track pages tested vs total pages

### Test Health Dashboard

```python
# Example metrics collection
{
    \"total_tests\": 16,
    \"passed\": 16,
    \"failed\": 0,
    \"pass_rate\": \"100%\",
    \"avg_duration\": \"4.1s\",
    \"total_duration\": \"66s\",
    \"portals\": {
        \"b2b\": {\"tests\": 8, \"passed\": 8, \"duration\": \"40s\"},
        \"b2c\": {\"tests\": 5, \"passed\": 5, \"duration\": \"14s\"},
        \"platform\": {\"tests\": 3, \"passed\": 3, \"duration\": \"12s\"}
    }
}
```

## Conclusion

Our E2E browser testing strategy focuses on **reliability over complexity**. Simple smoke tests provide a solid foundation that:

- ✅ Catches major regressions
- ✅ Runs fast (< 2 minutes)
- ✅ Requires minimal maintenance
- ✅ Scales across all portals

Expand gradually based on actual business needs rather than pursuing 100% coverage. Critical workflows should be tested thoroughly; rarely-used features can rely on manual testing initially.

**Next Steps:**
1. Run tests regularly in CI/CD
2. Add 1-2 critical workflow tests per sprint
3. Monitor flakiness and fix immediately
4. Keep tests simple and maintainable
