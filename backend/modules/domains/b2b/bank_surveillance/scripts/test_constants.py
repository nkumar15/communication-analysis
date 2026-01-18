"""
Quick test to verify constants import works
"""
import sys
sys.path.append("/app")

from modules.domains.b2b.bank_surveillance.constants import REGULATIONS_TENANT_ID

print(f"✅ REGULATIONS_TENANT_ID: {REGULATIONS_TENANT_ID}")
print(f"   Type: {type(REGULATIONS_TENANT_ID)}")
print(f"   UUID: {str(REGULATIONS_TENANT_ID)}")
