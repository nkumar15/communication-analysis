import asyncio
import sys
import json
sys.path.append("/app")

async def test_orchestrator():
    try:
        from modules.domains.enron.services.orchestrator import orchestrator_service
        
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
        print(f"  Risk Level: {report_1.risk_level}")
        print(f"  Requires Action: {report_1.requires_action}")
        print(f"  Intent: {report_1.intent_verdict.get('classification')}")
        print(f"  Policy Compliant: {report_1.policy_verdict.get('is_compliant') if report_1.policy_verdict else 'N/A'}")
        print(f"  Evasion Detected: {report_1.evasion_verdict.get('is_evasion') if report_1.evasion_verdict else 'N/A'}")
        print(f"  Summary: {report_1.summary}")
        
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
        print(f"  Risk Level: {report_2.risk_level}")
        print(f"  Requires Action: {report_2.requires_action}")
        print(f"  Intent: {report_2.intent_verdict.get('classification')}")
        print(f"  Evasion Type: {report_2.evasion_verdict.get('evasion_type') if report_2.evasion_verdict else 'N/A'}")
        print(f"  Summary: {report_2.summary[:100]}...")
        
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
        print(f"  Risk Level: {report_3.risk_level}")
        print(f"  Requires Action: {report_3.requires_action}")
        print(f"  Intent: {report_3.intent_verdict.get('classification')}")
        print(f"  Policy Check Run: {'Yes' if report_3.policy_verdict else 'No'}")
        print(f"  Summary: {report_3.summary}")
        
        # Test Case 4: Print Full Report as JSON (for API response validation)
        print("\n📄 Sample Full Report (JSON):")
        print(json.dumps(report_1.dict(), indent=2, default=str)[:500] + "...")
        
        print("\n✅ All orchestrator tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
