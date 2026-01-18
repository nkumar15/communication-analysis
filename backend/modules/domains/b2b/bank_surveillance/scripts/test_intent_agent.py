import asyncio
import sys
sys.path.append("/app")

async def test_intent_agent():
    try:
        from modules.domains.b2b.bank_surveillance.agents.intent_agent import intent_agent
        
        # Test Case 1: Fraud/Collusion - LJM Discussion
        email_1 = """
        From: Andrew Fastow
        To: Board Members
        Subject: LJM Partnership Structure
        
        The LJM2 special purpose entity will allow us to move debt off our balance sheet
        while maintaining control. We need to finalize the Raptor transactions before Q3 close.
        """
        
        print("\n🔍 Test 1: Fraud/Collusion (LJM/Raptor)")
        result_1 = await intent_agent.classify_email(email_1)
        print(f"   classification: {result_1.get('classification')}")
        print(f"   reasoning: {result_1.get('reasoning')[:100]}...")
        print(f"   confidence: {result_1.get('confidence')}")
        
        # Test Case 2: Evasion Attempt
        email_2 = """
        From: Ken Lay
        To: Jeff Skilling
        Subject: Urgent
        
        Don't send any more emails about the Chewco deal.
        Call me on my cell at 555-1234 and let's take this discussion offline.
        """
        
        print("\n🔍 Test 2: Evasion Attempt")
        result_2 = await intent_agent.classify_email(email_2)
        print(f"   classification: {result_2.get('classification')}")
        print(f"   reasoning: {result_2.get('reasoning')[:100]}...")
        print(f"   confidence: {result_2.get('confidence')}")
        
        # Test Case 3: Business as Usual (Newsletter)
        email_3 = """
        From: Corporate Communications
        To: All Staff
        Subject: Weekly News Digest
        
        This week's industry news:
        - Energy prices up 5%
        - New regulations on trading announced
        - Company picnic this Saturday!
        """
        
        print("\n🔍 Test 3: Business as Usual (Newsletter)")
        result_3 = await intent_agent.classify_email(email_3)
        print(f"   classification: {result_3.get('classification')}")
        print(f"   reasoning: {result_3.get('reasoning')[:100]}...")
        print(f"   confidence: {result_3.get('confidence')}")
        
        # Test Case 4: Business as Usual (Normal Work)
        email_4 = """
        From: Project Manager
        To: Team
        Subject: Project Update
        
        Great work on the presentation yesterday. Let's meet tomorrow at 2pm
        to review the client feedback and plan next steps.
        """
        
        print("\n🔍 Test 4: Business as Usual (Normal Work)")
        result_4 = await intent_agent.classify_email(email_4)
        print(f"   classification: {result_4.get('classification')}")
        print(f"   reasoning: {result_4.get('reasoning')[:100]}...")
        print(f"   confidence: {result_4.get('confidence')}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_intent_agent())
