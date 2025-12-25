
from typing import Optional
from infrastructure.auth.provider import AuthProvider
from infrastructure.auth.firebase import FirebaseAuthProvider

_auth_provider: Optional[AuthProvider] = None

def get_auth_provider() -> AuthProvider:
    """Factory to return the active authentication provider"""
    global _auth_provider
    if _auth_provider is None:
        from core.config import settings
        
        if settings.auth_provider == "firebase":
            from infrastructure.auth.firebase import FirebaseAuthProvider
            _auth_provider = FirebaseAuthProvider()
        else:
            # Fallback for now or raise error
            from infrastructure.auth.firebase import FirebaseAuthProvider
            _auth_provider = FirebaseAuthProvider()
            
        _auth_provider.initialize()
    return _auth_provider


_provisioner: Optional["TenantProvisioner"] = None

def get_tenant_provisioner() -> "TenantProvisioner":
    """Factory to return the active tenant provisioner"""
    global _provisioner
    if _provisioner is None:
        from core.config import settings
        
        # Avoid circular imports by importing interface here if needed, 
        # but better to use forward reference or TYPE_CHECKING
        
        if settings.auth_provider == "firebase":
            from infrastructure.auth.firebase_provisioning import FirebaseTenantProvisioner
            _provisioner = FirebaseTenantProvisioner()
        else:
            # Fallback
            from infrastructure.auth.firebase_provisioning import FirebaseTenantProvisioner
            _provisioner = FirebaseTenantProvisioner()
            
    return _provisioner

if False: # TYPE_CHECKING
    from infrastructure.auth.provisioning import TenantProvisioner
