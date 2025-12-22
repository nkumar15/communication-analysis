from playwright.async_api import Page
import pytest
import os
from tests.e2e_browser.pages.b2b.teams_page import TeamsPage

@pytest.mark.browser
@pytest.mark.asyncio
async def test_teams_list_load(authenticated_b2b_page: Page):
    """
    Test that the Teams page loads and displays the title and default team.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    teams_page = TeamsPage(authenticated_b2b_page, base_url)
    
    await teams_page.navigate()
    await teams_page.verify_loaded()
    await teams_page.verify_default_team_exists()

@pytest.mark.browser
@pytest.mark.asyncio
async def test_create_team_flow(authenticated_b2b_page: Page):
    """
    Test the flow of creating a new team.
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    teams_page = TeamsPage(authenticated_b2b_page, base_url)
    
    await teams_page.navigate()
    await teams_page.create_team("QA Automation Team", "Created by E2E Browser Test")
    await teams_page.verify_team_created("QA Automation Team")
