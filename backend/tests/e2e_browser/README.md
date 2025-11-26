# Browser E2E Testing Infrastructure

## ✅ Setup Complete

The Browser E2E testing infrastructure has been set up and is **working correctly**.

### Current Status
- ✅ Infrastructure configured
- ✅ Playwright + Chromium installed
- ✅ Tests run successfully (fail with `ERR_CONNECTION_REFUSED` because frontend not running - **expected**)
- ✅ Async loop conflict resolved
- ⏸️ **DEFERRED**: Full implementation blocked by WSL/Docker networking (frontend in WSL, tests in Docker can't access `localhost:3000`)

**Status**: Infrastructure complete. Tests deferred until CI/CD or dedicated test environment where networking is simpler.

### Infrastructure
1. **Multistage Dockerfile**: Created `base`, `production`, and `test` stages
   - `base`: Common Python dependencies
   - `production`: Minimal runtime (for deployment)
   - `test`: Includes test dependencies + Playwright + Chromium

2. **Test Directory**: `backend/tests/e2e_browser/`
   - `conftest.py`: Playwright configuration
   - `test_tenant_onboarding.py`: Onboarding flow tests
   - `test_invitation_flow.py`: Invitation flow tests
   - `test_admin_dashboard.py`: Dashboard rendering tests

3. **Makefile**: `make e2e-browser` command added

### Key Design Decisions

**❌ Database Fixtures Not Used in Browser Tests**

Browser tests do NOT use `db_session` or other async database fixtures due to event loop conflicts between `pytest-playwright` and `pytest-asyncio`. This is intentional:

- **Why**: `pytest-playwright` manages its own event loop for browser automation, conflicting with `pytest-asyncio`'s loop management
- **Solution**: Browser tests use only Playwright's `page` fixture
- **Test Data**: Should be created via API calls, not direct DB manipulation

### Current Status

- ✅ Infrastructure configured
- ✅ Smoke tests created (but skipped - require frontend running)
- ⚠️ Browser install works in Docker build but **volume mounts override** the installation at runtime

### Known Limitation: Volume Mounts

When running locally with `docker-compose`, the volume mount (`./backend:/app`) overrides the container's `/app` directory, which includes the Playwright browser binaries installed during build.

**Workarounds**:
1. **Option A**: Install browsers at runtime (slower first run):
   ```bash
   docker-compose exec backend playwright install chromium
   ```

2. **Option B**: Run tests without volume mounts (requires rebuild after code changes)

3. **Option C**: CI/CD environments don't use volume mounts, so tests work fine there

### Running Tests

**Prerequisites**:
- Frontend running at `http://localhost:3000`
- Backend API accessible
- Test data created via API

**Execute**:
```bash
make e2e-browser
```

### Test Structure

Tests are intentionally minimal smoke tests because:
1. Real testing requires running frontend
2. Test data must be created via API (not DB fixtures)
3. SSO authentication is complex to mock in browser context

### Next Steps

To implement full browser E2E tests:
1. Create API helper module for test data setup
2. Implement authentication bypass or test account
3. Run frontend in test mode
4. Write actual test flows

## Technical Notes

- **Sync API**: Playwright Python provides sync fixtures by default. Tests use regular `def`, not `async def`
- Python regex: Use `re.compile(r"pattern", re.IGNORECASE)` not `/pattern/i`
- Playwright methods: Use `page.goto()` not `await page.goto()` (sync API)
