import pytest
import json
from modules.domains.b2b.bank_surveillance.services.orchestrator import orchestrator_service

@pytest.mark.asyncio
async def test_orchestrator_scenarios():
    """
    Integration test for the Bank Surveillance Orchestrator.
    Evaluates emails for Risk, Intent, Policy Violation, and Evasion.
    """
    
    # Test Case 1: High Risk - Fraud + Policy Violation
    email_1 = """
    From: Andrew Fastow
    To: Board Members
    Subject: LJM Partnership
    
    The LJM2 special purpose entity structure allows us to keep debt off our balance sheet.
    We need to finalize the Raptor transactions before reporting season.
    This is exactly the kind of off-balance-sheet arrangement we discussed.
    """
    
    print("\n🔍 Test 1: High Risk Email (Fraud + Policy Violation)")
    report_1 = await orchestrator_service.investigate_email(email_1)
    # Basic assertions to ensure it ran
    assert report_1 is not None
    assert report_1.risk_level is not None
    
    # Test Case 2: High Risk - Evasion Attempt
    email_2 = """
    From: Ken Lay
    To: Jeff Skilling
    Subject: Urgent
    
    Don't email me about the Chewco deals anymore.
    Call my cell at 555-1234 and we'll take this offline.
    Delete this email after reading.
    """
    
    print("\n🔍 Test 2: High Risk Email (Evasion)")
    report_2 = await orchestrator_service.investigate_email(email_2)
    assert report_2 is not None

    # Test Case 3: Low Risk - Business as Usual
    email_3 = """
    From: HR Department
    To: All Staff
    Subject: Team Lunch
    
    Reminder: Team lunch tomorrow at noon in the cafeteria.
    Looking forward to seeing everyone there!
    """
    
    print("\n🔍 Test 3: Low Risk Email (Business as Usual)")
    report_3 = await orchestrator_service.investigate_email(email_3)
    assert report_3 is not None
    
    # Test Case 4: Print Full Report as JSON (for API response validation)
    print("\n📄 Sample Full Report (JSON):")
    print(json.dumps(report_1.dict(), indent=2, default=str)[:500] + "...")
