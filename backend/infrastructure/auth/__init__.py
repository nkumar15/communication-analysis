
from typing import Optional
from infrastructure.auth.provider import AuthProvider
from infrastructure.auth.firebase import FirebaseAuthProvider

_auth_provider: Optional[AuthProvider] = None

def get_auth_provider() -> AuthProvider:
    """Factory to return the active authentication provider.

    FirebaseAuthProvider is the only implementation — but its
    verify_id_token() accepts mock tokens (header.payload.mock_signature)
    in local/dev without needing a real Firebase project, so this covers
    both real and local/mock usage.
    """
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = FirebaseAuthProvider()
        _auth_provider.initialize()
    return _auth_provider


_provisioner: Optional["TenantProvisioner"] = None

def get_tenant_provisioner() -> "TenantProvisioner":
    """Factory to return the active tenant provisioner"""
    global _provisioner
    if _provisioner is None:
        from core.config import settings

        # Same local/dev detection used by FirebaseAuthProvider's mock-token
        # bypass: without a real Firebase project, tenant creation can't call
        # out to Identity Platform, so fall back to a local no-op provisioner.
        if settings.log_environment in ["local", "development"]:
            from infrastructure.auth.local_provisioning import LocalTenantProvisioner
            _provisioner = LocalTenantProvisioner()
        else:
            from infrastructure.auth.firebase_provisioning import FirebaseTenantProvisioner
            _provisioner = FirebaseTenantProvisioner()

    return _provisioner

if False: # TYPE_CHECKING
    from infrastructure.auth.provisioning import TenantProvisioner
