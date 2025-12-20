# Local E2E Testing Setup

Guide for running E2E browser tests locally outside of Docker.

**Last Updated:** 2025-12-20  
**Test Status:** 93.9% API tests passing | Browser tests in development

---

## Overview

This guide covers running E2E tests in your local development environment, useful for:
- Debugging test failures
- Developing new tests
- Running tests with visible browser (headed mode)
- Faster iteration during test development

---

## Testing Modes

### 1. API Tests (Recommended)

**Current Status:** 298 tests, 93.9% passing

**Run via Docker (Recommended):**
```bash
# Full suite
make test-api

# Specific service
make test-b2b
make test-platform
make test-b2c

# With coverage
make test-api-coverage

# Specific test file
docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/onboarding/test_activation.py -v
```

See [Test Matrix](../testing/test-matrix.md) for complete coverage details.

---

### 2. Browser Tests (Development)

**Status:** Partially implemented, some tests skipped  
**Technology:** Playwright

Run browser tests outside Docker for development and debugging.

---

## Setup for Local Testing

### Prerequisites

- Python 3.11+
- Backend running in Docker (`make up`)
- Test database available

### 1. Install Python Dependencies

```bash
# Using pip
pip install pytest pytest-playwright pytest-asyncio python-dotenv

# OR using uv (recommended)
uv pip install pytest pytest-playwright pytest-asyncio python-dotenv
```

### 2. Install Playwright Browsers

```bash
# Install browser binaries
playwright install

# Install system dependencies (Linux/WSL)
playwright install-deps
```

---

## Running Tests Locally

### Environment Setup

The backend requires environment variables. Set these before running tests:

```bash
# Required environment variables
export DATABASE_URL=postgresql+asyncpg://sso_user:sso_password@localhost:5433/sso_db
export SECRET_KEY=test-secret-key-123
export FIREBASE_PROJECT_ID=test-project
export BACKEND_URL=http://localhost:8080
export FRONTEND_URL=http://localhost:3000
```

**Quick setup script:**
```bash
#!/bin/bash
# save as: scripts/setup-test-env.sh

export DATABASE_URL=postgresql+asyncpg://sso_user:sso_password@localhost:5433/sso_db
export SECRET_KEY=test-secret-key-123
export FIREBASE_PROJECT_ID=test-project
export GOOGLE_APPLICATION_CREDENTIALS=secrets/firebase-credentials.json
export BACKEND_URL=http://localhost:8080
export FRONTEND_URL=http://localhost:3000

echo "Test environment configured ✅"
```

**Usage:**
```bash
source scripts/setup-test-env.sh
```

---

## Running Tests

### API Tests (Local Python)

```bash
# 1. Start backend
make up

# 2. Setup environment
source scripts/setup-test-env.sh

# 3. Run tests from project root
cd backend
pytest tests/e2e_api/b2b/onboarding/ -v

# Run with specific markers
pytest -m "not slow" -v

# Run single test
pytest tests/e2e_api/b2b/onboarding/test_activation.py::test_validate_valid_token -v
```

### Browser Tests (Headed Mode)

```bash
# Run in headed mode (visible browser)
pytest tests/e2e_browser/b2c/ --headed

# Run with slow motion (for debugging)
pytest tests/e2e_browser/b2c/ --headed --slowmo 2000

# Run specific browser
pytest tests/e2e_browser/ --browser chromium --headed
```

---

## Platform-Specific Instructions

### WSL (Windows Subsystem for Linux)

**Additional requirements for headed mode:**

1. **Install X Server (Windows):**
   - Download [VcXsrv](https://sourceforge.net/projects/vcxsrv/)
   - Launch XLaunch, keep defaults, **disable access control**

2. **Configure WSL display:**
   ```bash
   export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
   ```

3. **Add to .bashrc for persistence:**
   ```bash
   echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk "{print \\$2}"):0' >> ~/.bashrc
   ```

4. **Run tests:**
   ```bash
   pytest tests/e2e_browser/ --headed
   ```

### Windows (Native PowerShell)

For native Windows development (React Native, etc.):

**Setup:**
```powershell
# 1. Start Docker services (in WSL or Docker Desktop)
docker-compose up -d

# 2. Navigate to backend
cd backend

# 3. Create virtual environment
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1

# 4. Install dependencies
pip install -r requirements-test.txt
playwright install

# OR using uv
uv venv
uv pip install -r requirements-test.txt
uv run playwright install
```

**Run tests:**
```powershell
# Using activated venv
pytest tests/e2e_browser/ --headed --slowmo 2000

# Using uv (no activation needed)
uv run pytest tests/e2e_browser/ --headed --slowmo 2000
```

**Fix execution policy error:**
```powershell
# Run as Administrator
Set-ExecutionPolicy RemoteSigned
```

### macOS

```bash
# Install Python dependencies
pip3 install pytest pytest-playwright pytest-asyncio python-dotenv

# Install browsers
playwright install

# Run tests
pytest tests/e2e_browser/ --headed
```

---

## Debugging Tests

### Pytest Options

```bash
# Show print statements
pytest -s tests/e2e_api/

# Stop on first failure
pytest -x tests/e2e_api/

# Run last failed tests
pytest --lf

# Show locals in tracebacks
pytest -l tests/e2e_api/

# Verbose output
pytest -vv tests/e2e_api/
```

### Playwright Debugging

```bash
# Debug mode (pause before each action)
PWDEBUG=1 pytest tests/e2e_browser/ --headed

# Slow motion (milliseconds between actions)
pytest tests/e2e_browser/ --headed --slowmo 2000

# Take screenshots on failure
pytest tests/e2e_browser/ --screenshot on

# Save trace for debugging
pytest tests/e2e_browser/ --tracing on
```

### Database Debugging

```bash
# Check database state
docker-compose exec postgres psql -U sso_user -d sso_db

# Quick queries
docker-compose exec postgres psql -U sso_user -d sso_db -c \\
  "SELECT id, name, activation_status FROM b2b.tenants;"

# Reset database
make reset-db
```

---

## Troubleshooting

### Common Issues

#### "DATABASE_URL environment variable not set"

**Cause:** Missing environment configuration

**Fix:**
```bash
source scripts/setup-test-env.sh
# OR set manually
export DATABASE_URL=postgresql+asyncpg://sso_user:sso_password@localhost:5433/sso_db
```

#### "Connection refused" errors

**Cause:** Backend not running or wrong port

**Fix:**
1. Ensure backend is running: `make up`
2. Check ports: `docker-compose ps`
3. Verify DATABASE_URL uses `localhost` not `postgres`

#### "ModuleNotFoundError"

**Cause:** Missing dependencies or wrong directory

**Fix:**
```bash
# Install all test dependencies
pip install -r backend/requirements-test.txt

# Run from backend directory
cd backend
pytest tests/
```

#### Browser tests fail on WSL

**Cause:** No display server or browser not installed

**Fix:**
1. Install X Server (VcXsrv)
2. Set DISPLAY variable
3. Run: `playwright install-deps`

#### "Permission denied" (PowerShell)

**Cause:** Execution policy restriction

**Fix (as Administrator):**
```powershell
Set-ExecutionPolicy RemoteSigned
```

---

## CI/CD Integration

Tests run automatically in CI using the Docker-based approach:

```yaml
# .github/workflows/tests.yml
- name: Run E2E Tests
  run: make test-api

- name: Upload Coverage
  run: make test-api-coverage
```

**Test Artifacts:**
- Coverage reports: `backend/htmlcov/`
- Test results: JUnit XML format
- Screenshots (browser tests): `test-results/`

---

## Performance Tips

### Speed Up Test Runs

1. **Run specific tests:**
   ```bash
   # Only B2B onboarding
   pytest tests/e2e_api/b2b/onboarding/ -v
   ```

2. **Use markers:**
   ```bash
   # Skip slow tests
   pytest -m "not slow"
   ```

3. **Parallel execution:**
   ```bash
   # Install pytest-xdist
   pip install pytest-xdist
   
   # Run with 4 workers
   pytest -n 4 tests/e2e_api/
   ```

4. **Reuse containers:**
   ```bash
   # Don't recreate containers
   make test-api  # uses existing containers
   ```

---

## Best Practices

1. **Always reset database** when testing tenant creation
2. **Use fixtures** from `conftest.py` for setup
3. **Set RLS context** for database queries in tests
4. **Clean up after tests** (use fixtures with yield)
5. **Use descriptive test names** following `test_<action>_<expected_outcome>`
6. **Add docstrings** to tests explaining the scenario
7. **Use markers** to categorize tests (`@pytest.mark.slow`)

---

## Additional Resources

- **[Test Matrix](../testing/test-matrix.md)** - Complete test coverage mapping
- **[Testing Strategy](../testing/strategy.md)** - Overall testing approach
- **[B2B E2E Activation Guide](../testing/b2b-e2e-activation.md)** - Manual activation testing
- **[Development Guide](./development.md)** - Complete development workflow
- **[Playwright Docs](https://playwright.dev/python/)** - Browser testing framework

---

**Questions?** See [Development Guide](./development.md) or check test logs: `make logs`
