import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def enforce_use_case():
    """Ensure tests in this directory run with bank_surveillance use case"""
    current_case = os.getenv("USE_CASE")
    
    # Default is bank_surveillance, so if not set, it's fine.
    # If set to something else (e.g. task_management), skip.
    if current_case and current_case != "bank_surveillance":
        pytest.skip(f"Skipping bank_surveillance tests (USE_CASE={current_case})")
