from modules.domains.b2b.bank_surveillance.constants import REGULATIONS_TENANT_ID

def test_constants_loaded():
    """Verify constants import correctly"""
    assert REGULATIONS_TENANT_ID is not None
    print(f"✅ REGULATIONS_TENANT_ID: {REGULATIONS_TENANT_ID}")
