import pytest
from playwright.async_api import Page, expect
import os

# Use the frontend URL from environment or default to localhost:3000
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context arguments.
    Set viewport size and base URL.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "base_url": FRONTEND_URL,
        "ignore_https_errors": True,
    }
