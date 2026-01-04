
import asyncio
import sys
import os

# Add /app to sys.path
sys.path.append("/app")

async def test_agent():
    try:
        from modules.domains.enron.agents.policy_agent import policy_agent
        
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
        print("RESULT 1:")
        print(result)
        
        # Test Case 2: Benign
        email_text_2 = """
        From: HR
        To: All Employees
        Subject: Picnic
        
        Don't forget the company picnic this Saturday!
        """
        
        print("\nZooming into Email 2 (Picnic)...")
        result_2 = await policy_agent.analyze_email(email_text_2)
        print("RESULT 2:")
        print(result_2)

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print(f"Sys Path: {sys.path}")
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
    
if __name__ == "__main__":
    asyncio.run(test_agent())
