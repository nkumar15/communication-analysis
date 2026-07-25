---
description: Steps to run E2E API and Browser tests using Docker and Pytest.
---

## 1. Start Environment
// turbo
- Start all backend services: `make up`

## 2. Run API Tests
**Separation Logic**: The system knows to run only API tests because `make test-api` specifically targets the `tests/e2e_api/` directory.

- **Run all API integration tests**:
  `make test-api`

- **Run specific API module (e.g., Billing)**:
  `docker-compose run --rm e2e-tests pytest tests/e2e_api/b2b/billing/ -v`

## 3. Run Browser Tests
**Separation Logic**: Browser tests reside in the `tests/e2e_browser/` directory. Make commands automate the frontend container startup required for these tests.

- **Run all browser tests**:
  `make test-browser`

- **Run B2B browser tests only**:
  `make test-browser-b2b`

- **Run specific browser test file**:
  `make test-browser-b2b TEST_PATH=tests/e2e_browser/b2b/test_login.py`

## 4. Run Everything
- **Run all API and Browser tests**:
  `make test`

## 5. Troubleshooting
- **Logs**: `make logs s=b2b-api` or `make logs s=e2e-tests`
- **DB Check**: `make status`
