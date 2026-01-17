import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def enforce_use_case():
    """Ensure tests in this directory run with task_management use case"""
    current_case = os.getenv("USE_CASE")
    if current_case and current_case != "task_management":
        pytest.skip(f"Skipping task_management tests (USE_CASE={current_case})")
    
    # If not set, we assume we are running this specific directory or via make test-b2b-task
    # But wait, seed_db runs at session start globally.
    # Changing env var here won't affect seed_db if it already ran!
    
    # Correct approach:
    # Option B relies on separate test runs:
    # make test-b2b-task -> sets USE_CASE=task_management -> seed_db reads it -> seeds task mgmt -> tests run.
    # make test-b2b -> sets USE_CASE=bank -> seed_db seeds bank -> this fixture skips these tests.
    
    pass
