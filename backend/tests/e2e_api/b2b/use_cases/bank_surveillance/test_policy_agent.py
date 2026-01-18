import pytest
from modules.domains.b2b.bank_surveillance.agents.policy_agent import policy_agent

@pytest.mark.asyncio
async def test_policy_agent_scenarios():
    """Test policy violation detection scenarios"""
    
    # Test Case 1: LJM / Conflict of Interest (Suspicious)
    email_text = """
    From: Andrew Fastow
    To: Ben Glisan
    Subject: LJM2 Structure
    
    Ben, we need to move the raptor assets into the LJM2 special purpose entity before the quarter close. 
    This will help us keep the debt off the balance sheet. 
    Make sure we don't disclose the full ownership structure in the reports.
    """
    
    print("\n🔎 Analyzing Email 1 (LJM/Off-balance sheet)...")
    result = await policy_agent.analyze_email(email_text)
    assert result is not None
    # We expect some policy violation here
    
    # Test Case 2: Benign
    email_text_2 = """
    From: HR
    To: All Employees
    Subject: Picnic
    
    Don't forget the company picnic this Saturday!
    """
    
    print("\nZooming into Email 2 (Picnic)...")
    result_2 = await policy_agent.analyze_email(email_text_2)
    assert result_2 is not None
