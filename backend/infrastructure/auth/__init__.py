
from typing import Optional
from infrastructure.auth.provider import AuthProvider
from infrastructure.auth.firebase import FirebaseAuthProvider

_auth_provider: Optional[AuthProvider] = None

def get_auth_provider() -> AuthProvider:
    """Factory to return the active authentication provider"""
    global _auth_provider
    if _auth_provider is None:
        # In future, we could switch on settings.AUTH_PROVIDER
        _auth_provider = FirebaseAuthProvider()
        _auth_provider.initialize()
    return _auth_provider

# Backward compatibility (optional, but helpful for refactoring)
# We can expose the singleton directly for now, which mimics the old behavior
firebase_auth_service = get_auth_provider()
