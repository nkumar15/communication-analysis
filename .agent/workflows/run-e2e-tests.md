---
description: Steps to run E2E API and Browser tests using Docker and Pytest.
---

1.  **Start Environment**
    // turbo
    - Clean up any stale containers: `docker-compose down`
    // turbo
    - Start all services in detached mode: `docker-compose up -d`
    // turbo
    - Wait for services to be healthy (manual check or sleep 10s).

2.  **Run API Tests**
    - Run specific API test file: `pytest backend/tests/e2e_api/test_{name}.py -v`
    - OR run all API tests: `pytest backend/tests/e2e_api/ -v`

3.  **Run Browser Tests**
    - Run specific browser test: `pytest backend/tests/e2e_browser/test_{name}.py -v`
    - OR run all browser tests: `pytest backend/tests/e2e_browser/ -v`

4.  **Troubleshooting**
    - If tests fail on DB connection, ensure Postgres is healthy: `docker ps`
    - If tests fail on Auth, check `conftest.py` mock token generation.
