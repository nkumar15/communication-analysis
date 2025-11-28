# E2E Browser Tests - Setup Guide

## Overview

The E2E browser tests use **real Firebase authentication** with custom tokens to automate login flows. This approach:
- Uses your actual Firebase GCIP configuration
- Bypasses the OAuth popup/redirect flow (which is hard to automate)
- Still validates the full authentication stack

## Prerequisites

1. **System Tenant**: You must have a system tenant configured in Firebase GCIP
2. **Firebase Credentials**: Valid `firebase-credentials.json` in the `secrets/` directory
3. **Platform Admin**: A platform admin user created via `make create-platform-admin`

## Configuration

Set these environment variables before running tests (or use defaults):

```bash
export E2E_SYSTEM_TENANT_ID="your-system-tenant-id"
export E2E_SYSTEM_OIDC_PROVIDER="your-oidc-provider-id"
export E2E_PLATFORM_ADMIN_EMAIL="admin@platform.test"
```

## Running Tests

```bash
# Run all E2E browser tests
make e2e-browser

# Run specific test file
docker-compose run --rm e2e-tests python -m pytest tests/e2e_browser/test_platform_admin.py -v
```

## How It Works

1. **Custom Tokens**: Tests use Firebase Admin SDK to create custom tokens
2. **Frontend Login**: Tests inject the custom token into the browser and call `signInWithCustomToken()`
3. **Real Auth**: The backend validates these tokens using Firebase Admin SDK as normal
4. **No Popups**: Bypasses the OAuth redirect/popup flow entirely

## Test Structure

```
tests/e2e_browser/
├── e2e_config.py       # Configuration (tenant IDs, URLs)
├── e2e_helpers.py      # Token generation utilities
├── conftest.py         # Playwright fixtures
├── test_platform_admin.py
├── test_tenant_onboarding.py
└── test_invitation_flow.py
```

## Writing New Tests

```python
from e2e_helpers import create_platform_admin_token
from e2e_config import PLATFORM_ADMIN_EMAIL

def test_example(page: Page):
    # Get custom token
    token = await create_platform_admin_token(PLATFORM_ADMIN_EMAIL)
    
    # Navigate and inject token
    page.goto("/platform-login")
    page.evaluate(f"localStorage.setItem('custom_token', '{token}')")
    
    # Frontend code should check for custom_token and use signInWithCustomToken()
    # ... rest of test
```

## Troubleshooting

**"Invalid custom token" errors**:
- Ensure Firebase credentials are correct
- Check that the tenant ID in the token matches the system tenant

**"User not found" errors**:
- Make sure the platform admin user exists in the database
- Run `make create-platform-admin` if needed

**Tests timing out**:
- Check that services are running: `docker-compose ps`
- View logs: `docker-compose logs frontend backend`
