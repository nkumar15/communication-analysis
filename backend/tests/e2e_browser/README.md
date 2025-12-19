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
make test-browser

# Run specific suites (Recommended)
make test-browser-b2c       # B2C Signup & Workspace
make test-browser-b2b       # B2B Invites & Roles
make test-browser-platform  # Admin & Tenant Mgmt

# Run with visual browser (Local Only)
# Note: Requires running pytest locally, or X11 forwarding for Docker
make test-browser-b2c HEADED=1
```

## How It Works

1. **Custom Tokens**: Tests use Firebase Admin SDK to create custom tokens
2. **Frontend Login**: Tests inject the custom token into the browser and call `signInWithCustomToken()`
3. **Real Auth**: The backend validates these tokens using Firebase Admin SDK as normal
4. **No Popups**: Bypasses the OAuth redirect/popup flow entirely

## Test Structure

We follow a Domain-Driven structure with Page Object Models (POM).

```
tests/e2e_browser/
├── conftest.py                 # Global fixtures (browser, context)
├── e2e_config.py               # Shared config
├── e2e_helpers.py              # Auth helpers
│
├── pages/                      # Page Object Models
│   ├── base_page.py            # Base interactions
│   ├── b2c/
│   │   ├── signup_page.py
│   │   └── workspace_page.py
│   └── platform/
│       └── login_page.py
│
├── platform/                   # Platform Admin Tests
│   └── test_platform_admin.py
│
├── b2b/                        # B2B Tenant Tests
│   └── test_invitation_flow.py
│
└── b2c/                        # B2C Tests
    ├── conftest.py             # B2C specific fixtures
    └── test_signup_flow.py
```

## Writing New Tests

### Using Page Objects (Recommended)

```python
from ..e2e_helpers import create_custom_token
from ..pages.b2c.signup_page import SignupPage

async def test_new_feature(page: Page):
    # Setup
    token = await create_custom_token(...)
    signup_page = SignupPage(page)
    
    # Act
    signup_page.sign_in_with_google_mock(token)
    
    # Assert
    signup_page.is_dashboard_visible()
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
