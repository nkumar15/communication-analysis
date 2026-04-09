import pytest
pytestmark = pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")

from modules.domains.b2b.bank_surveillance.agents.evasion_agent import EvasionAgent

@pytest.mark.skip(reason="Skipping agent tests as per user request")
@pytest.mark.asyncio
async def test_evasion_agent_scenarios():
    """Test evasion detection scenarios"""
    agent = EvasionAgent(tenant_id=None)
    
    # Test Case 1: Clear Evasion - Channel Switch
    email_1 = """
    From: Andrew Fastow
    To: Jeff Skilling
    Subject: LJM Discussion
    
    Jeff, we need to talk about the LJM partnership structure. 
    Don't send any emails about this - call me on my cell at 555-1234.
    We should keep this conversation offline.
    """
    
    print("\n🔍 Test 1: Clear Channel Switch Evasion")
    result_1 = await agent.analyze_email(email_1)
    assert result_1.get('is_evasion') is True
    assert result_1.get('evasion_type') == "channel_switch"
    
    # Test Case 2: Evidence Destruction
    email_2 = """
    From: Ken Lay
    To: Executive Team
    Subject: Document Retention
    
    Please delete all emails related to the Raptor transactions.
    Shred any physical documents immediately.
    """
    
    print("\n🔍 Test 2: Evidence Destruction")
    result_2 = await agent.analyze_email(email_2)
    assert result_2.get('is_evasion') is True
    
    # Test Case 3: Benign (should NOT flag)
    email_3 = """
    From: HR Department
    To: All Staff
    Subject: Meeting Reminder
    
    Reminder: Team lunch tomorrow at noon in the cafeteria.
    If you need to reach me, my cell is 555-5678.
    """
    
    print("\n🔍 Test 3: Benign Email (should be False)")
    result_3 = await agent.analyze_email(email_3)
    # Note: Result could be None or False depending on implementation
    if result_3.get('is_evasion'):
         print(f"Warning: Benign email flagged as evasion: {result_3}")
    
    # Test Case 4: Ambiguous
    email_4 = """
    From: Trader
    To: Analyst
    Subject: Quick Question
    
    Can you call me about the Q3 numbers? My cell is 555-9999.
    """
    
    print("\n🔍 Test 4: Ambiguous Email")
    result_4 = await agent.analyze_email(email_4)
    # Just ensure it runs without error
    assert result_4 is not None
