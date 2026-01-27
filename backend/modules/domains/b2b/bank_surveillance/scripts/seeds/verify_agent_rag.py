import asyncio
import sys
import os
import uuid

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../")))

from modules.domains.b2b.bank_surveillance.services.orchestrator import orchestrator_service

DEMO_TENANT_ID = uuid.UUID("b5e1fa40-89f4-50c2-a3f4-4c122000beef")

# Test Email simulating Enron Entity Fraud discussion
TEST_EMAIL = """
From: a..howard@enron.com
To: fastow@enron.com
Subject: LJM2 Capital - Raptor Structure

Andy,
Regarding the off-balance sheet vehicles we discussed. 
The special purpose entity (SPE) needs to be capitalized with Enron stock to hedge the Rhythms NetConnections investment.
Ensure the accounting treatment keeps this debt off our books.
We need to finalize the Raptor structure by quarter end.
"""

async def verify_agent():
    print("🤖 Verifying Policy Agent with Regulatory RAG...")
    
    # 1. Define Context (Simulating an Alert)
    metadata = {
        "sender": "a..howard@enron.com",
        "date": "2001-11-27",
        # THIS IS KEY: We inject the risk context to guide the agent
        "risk_indicators": ["Off-Balance Sheet", "Special Purpose Entity"] 
    }
    
    print(f"   Context Injected: {metadata['risk_indicators']}")
    print("   Analyzing email...")
    
    # 2. Run Investigation
    report = await orchestrator_service.investigate_email(
        email_text=TEST_EMAIL,
        email_metadata=metadata,
        tenant_id=DEMO_TENANT_ID
    )
    
    # 3. Print Results
    print("\n✅ Investigation Complete!")
    print(f"   Risk Level: {report.risk_level.upper()}")
    
    if report.policy_verdict:
        pv = report.policy_verdict
        print("\n📜 Policy Verdict:")
        print(f"   Compliant: {pv.get('is_compliant')}")
        print(f"   Violation: {pv.get('violation_citation')}")
        print(f"   Reasoning: {pv.get('reasoning')}")
        

        # 4. Verify RAG Usage
        reasoning = pv.get('reasoning', '').lower()
        if "sox" in reasoning or "companies act" in reasoning or "finance" in reasoning:
             print("\n✨ SUCCESS: Agent cited relevant regulations!")
        else:
             print("\n⚠️  WARNING: Agent might have missed the specific regulation.")

if __name__ == "__main__":
    asyncio.run(verify_agent())
