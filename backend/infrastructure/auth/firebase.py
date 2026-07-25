
import firebase_admin
from firebase_admin import auth, credentials
from typing import Optional, Dict, Any
from core.config import settings
from infrastructure.auth.provider import AuthProvider
from infrastructure.logging import get_logger

logger = get_logger(__name__)

class FirebaseAuthProvider(AuthProvider):
    """Firebase implementation of AuthProvider"""

    def __init__(self):
        self.app: Optional[firebase_admin.App] = None

    def initialize(self):
        """Initialize Firebase Admin SDK.

        In local/dev environments, a missing or invalid service account
        cert doesn't block startup — verify_id_token()'s mock-token path
        (header.payload.mock_signature) doesn't need a real Firebase app.
        Any code path that *does* need real Firebase (production, or the
        real-token branch of verify_id_token) will fail loudly at the
        point of use instead.
        """
        if firebase_admin._apps:
            return
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path_resolved)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            if settings.log_environment in ["local", "development"]:
                logger.warning(
                    "firebase_init_skipped",
                    reason=str(e),
                    note="No valid Firebase credentials — only mock tokens will work",
                )
            else:
                raise
    
    async def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify Firebase ID token
        """
        
        # MOCK AUTH BYPASS (For Load Testing/Local Dev only)
        if settings.log_environment in ["local", "development"]:
            try:
                # Check for mock signature format
                parts = id_token.split(".")
                if len(parts) == 3 and parts[2] == "mock_signature":
                    import json
                    import base64
                    
                    payload_segment = parts[1]
                    pad = len(payload_segment) % 4
                    if pad > 0:
                        payload_segment += "=" * (4 - pad)
                        
                    payload = json.loads(base64.urlsafe_b64decode(payload_segment))
                    return payload
            except Exception:
                pass

        try:
            # Firebase Admin SDK has built-in 5-minute clock skew tolerance
            from infrastructure.monitoring import record_token_validation
            with record_token_validation(provider="firebase"):
                decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=50)
            return decoded_token
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def get_user_info(self, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from decoded token"""
        return {
            "firebase_uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False),
            "firebase_tenant_id": decoded_token.get("firebase", {}).get("tenant"),
        }
    
    def create_custom_token(self, uid: str, tenant_id: str, claims: Optional[Dict[str, Any]] = None) -> bytes:
        """Create a Firebase custom token"""
        try:
            from firebase_admin import tenant_mgt
            tenant_client = tenant_mgt.auth_for_tenant(tenant_id)
            custom_token = tenant_client.create_custom_token(
                uid=uid,
                developer_claims=claims
            )
            return custom_token
        except Exception as e:
            raise ValueError(f"Failed to create custom token: {str(e)}")
