import asyncio
import sys
sys.path.append("/app")

async def test_evasion_agent():
    try:
        from modules.domains.b2b.bank_surveillance.agents.evasion_agent import evasion_agent
        
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
        result_1 = await evasion_agent.analyze_email(email_1)
        print(f"   is_evasion: {result_1.get('is_evasion')}")
        print(f"   evasion_type: {result_1.get('evasion_type')}")
        print(f"   evidence: {result_1.get('evidence')}")
        print(f"   confidence: {result_1.get('confidence')}")
        
        # Test Case 2: Evidence Destruction
        email_2 = """
        From: Ken Lay
        To: Executive Team
        Subject: Document Retention
        
        Please delete all emails related to the Raptor transactions.
        Shred any physical documents immediately.
        """
        
        print("\n🔍 Test 2: Evidence Destruction")
        result_2 = await evasion_agent.analyze_email(email_2)
        print(f"   is_evasion: {result_2.get('is_evasion')}")
        print(f"   evasion_type: {result_2.get('evasion_type')}")
        print(f"   evidence: {result_2.get('evidence')}")
        
        # Test Case 3: Benign (should NOT flag)
        email_3 = """
        From: HR Department
        To: All Staff
        Subject: Meeting Reminder
        
        Reminder: Team lunch tomorrow at noon in the cafeteria.
        If you need to reach me, my cell is 555-5678.
        """
        
        print("\n🔍 Test 3: Benign Email (should be False)")
        result_3 = await evasion_agent.analyze_email(email_3)
        print(f"   is_evasion: {result_3.get('is_evasion')}")
        print(f"   evasion_type: {result_3.get('evasion_type')}")
        print(f"   confidence: {result_3.get('confidence')}")
        
        # Test Case 4: Ambiguous
        email_4 = """
        From: Trader
        To: Analyst
        Subject: Quick Question
        
        Can you call me about the Q3 numbers? My cell is 555-9999.
        """
        
        print("\n🔍 Test 4: Ambiguous Email")
        result_4 = await evasion_agent.analyze_email(email_4)
        print(f"   is_evasion: {result_4.get('is_evasion')}")
        print(f"   evasion_type: {result_4.get('evasion_type')}")
        print(f"   evidence: {result_4.get('evidence')}")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_evasion_agent())
