import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from llama_index.core.schema import Document
from modules.domains.b2c.finance_trader.services.parsers.nse_parser import NSEEarningsParser

def test_transcript_parser():
    print("Testing Transcript Parser...")
    
    transcript_text = """
EARNINGS CALL Q2 FY24
---
Operator:
Welcome to the conference call. I now hand over to management.

Management:
Thank you. We had a great quarter. EBITDA is up 20%.

Analyst:
Can you explain the margin drop?

Management:
It was due to one-time costs.
    """
    
    doc = Document(text=transcript_text, metadata={"file_name": "test.txt"})
    parser = NSEEarningsParser()
    
    nodes = parser.get_nodes_from_documents([doc])
    
    print(f"Nodes generated: {len(nodes)}")
    for node in nodes:
        role = node.metadata.get("speaker_role", "Unknown")
        content = node.text[:50].replace("\n", " ")
        print(f"[{role}] {content}...")
        
    # Validation
    roles = [n.metadata.get("speaker_role") for n in nodes]
    expected_roles = ["Operator", "Management", "Analyst", "Management"]
    
    # Filter out Intro if any
    roles = [r for r in roles if r in expected_roles]
    
    if any(r in roles for r in expected_roles):
        print("SUCCESS: Found expected roles.")
    else:
        print("FAILURE: Roles not found correctly.")

if __name__ == "__main__":
    test_transcript_parser()
