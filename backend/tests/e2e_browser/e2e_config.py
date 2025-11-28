"""
E2E Test Configuration

Configuration for E2E browser tests using real Firebase authentication.
System tenant details should be configured via environment variables.
"""
import os

# System Tenant Configuration (read from environment or use defaults)
SYSTEM_TENANT_ID = os.getenv("E2E_SYSTEM_TENANT_ID", "system-platform")
SYSTEM_OIDC_PROVIDER = os.getenv("E2E_SYSTEM_OIDC_PROVIDER", "system-oidc")
PLATFORM_ADMIN_EMAIL = os.getenv("E2E_PLATFORM_ADMIN_EMAIL", "admin@platform.test")

# Test User Configuration (for tenant tests)
TEST_USER_EMAIL = os.getenv("E2E_TEST_USER_EMAIL", "test-user@example.com")

# Frontend/Backend URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:3000")
API_URL = os.getenv("API_URL", "http://backend:8000")
