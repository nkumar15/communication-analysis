# Local E2E Testing Setup (WSL)

To run **Headed** browser tests (where you see the Chrome window pop up) from WSL, follow these steps.

## 1. Install Python Dependencies
You need Python 3.10+ installed in WSL.

```bash
# Install pip dependencies
pip install pytest pytest-playwright pytest-asyncio python-dotenv

# OR if you use uv (recommended)
uv pip install pytest pytest-playwright pytest-asyncio python-dotenv
```

## 2. Install Playwright Browsers
This downloads the Chromium/Firefox binaries managed by Playwright.

```bash
playwright install
```

## 3. Install System Dependencies
WSL needs some Linux libraries to run the browser.

```bash
playwright install-deps
```

## 4. Run Tests Locally
Your backend requires certain environment variables to start. Source them from your backend `.env` file before running the test.

> [!IMPORTANT]
> The backend `.env` file might have `postgres` as the hostname. Locally, you need to use `localhost`.

### A. One-Liner (Recommended)
This command sets the necessary variables override to point to localhost, and runs the test.

```bash
# Export variables and run (Assuming you are in project root)
export DATABASE_URL=postgresql://saas_user:saas_user_password@localhost:5433/sso_db
export SECRET_KEY=test-secret-key-123
export FIREBASE_PROJECT_ID=test-project
export BACKEND_URL=http://localhost:8000
export FRONTEND_URL=http://localhost:3000

# Run the test
pytest backend/tests/e2e_browser/b2c/ --headed
```

### B. Why did it fail before?
The validation error happened because your local Python environment tried to load `backend/core/config.py`, which validates that `DATABASE_URL` and `SECRET_KEY` exist. Since you weren't running inside Docker (where these are set automatically), Pydantic raised an error.

---

# Windows (Native PowerShell)

If you are running on Windows directly (not WSL), you cannot use `make`. Use these commands in **PowerShell**.

## 1. Setup Environment
Open PowerShell in the `enterprisesso` root folder.

```powershell
# 1. Start Docker Services (Backend)
docker-compose up -d postgres b2b-api platform-api b2c-api domain-api nginx

# 2. Enter Backend Directory
cd backend

# 3. Create Virtual Env (If not exists)
# Standard Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# OR if using uv
uv venv

# 4. Install Dependencies
# Standard
pip install -r requirements-test.txt
playwright install

# OR using uv (Ensure you are in 'backend' folder)
uv pip install -r requirements-test.txt
uv run playwright install

```

## 2. Run Tests
Run the tests using `pytest`. The configuration already defaults to `localhost`.

### A. Using Active Venv
```powershell
pytest tests/e2e_browser/b2c/ --headed --slowmo 2000
```

### B. Using uv run (No activation needed)
```powershell
uv run pytest tests/e2e_browser/b2c/ --headed --slowmo 2000
```

> **Note:** If you see "Execution of scripts is disabled", run this as Admin:
> `Set-ExecutionPolicy RemoteSigned`
