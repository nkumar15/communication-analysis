import firebase_admin
from firebase_admin import auth, credentials
from typing import Optional, Dict, Any
from core.config import settings


class FirebaseAuthService:
    """Service for Firebase authentication"""
    
    def __init__(self):
        self.app: Optional[firebase_admin.App] = None
    
    def initialize(self):
        """Initialize Firebase Admin SDK"""
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.firebase_credentials_path_resolved)
            firebase_admin.initialize_app(cred)
    
    async def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify Firebase ID token
        
        Args:
            id_token: Firebase ID token from frontend
            
        Returns:
            Decoded token claims
            
        Raises:
            ValueError: If token is invalid
        """


        
        # MOCK AUTH BYPASS (For Load Testing/Local Dev only)
        if settings.log_environment in ["local", "development"]:
            try:
                # Check for mock signature format from utils.encode_mock_jwt
                # format: header.payload.signature
                parts = id_token.split(".")
                if len(parts) == 3 and parts[2] == "mock_signature":
                    import json
                    import base64
                    
                    # Store payload parts
                    payload_segment = parts[1]
                    
                    # Add padding if needed
                    pad = len(payload_segment) % 4
                    if pad > 0:
                        payload_segment += "=" * (4 - pad)
                        
                    # Decode payload
                    payload = json.loads(base64.urlsafe_b64decode(payload_segment))
                    return payload
            except Exception:
                # Fallthrough to real verification if anything fails
                pass

        try:
            # Firebase Admin SDK has built-in 5-minute clock skew tolerance
            from core.observability.metrics import record_token_validation
            with record_token_validation(provider="firebase"):
                decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=50)
            return decoded_token
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def get_user_info(self, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from decoded token
        
        Args:
            decoded_token: Decoded Firebase ID token
            
        Returns:
            User information dict with uid, email, name, tenant_id
        """
        return {
            "firebase_uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False),
            "firebase_tenant_id": decoded_token.get("firebase", {}).get("tenant"),
        }
    
    def create_custom_token(self, uid: str, tenant_id: str, claims: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Create a Firebase custom token for a given user in a specific tenant
        
        Args:
            uid: Firebase user ID
            tenant_id: Firebase tenant ID (e.g., 'firstcompany-99oyw')
            claims: Optional additional claims to include in the token
            
        Returns:
            Custom token as bytes
        """
        try:
            # For multi-tenant Firebase, get a tenant-aware auth client
            from firebase_admin import tenant_mgt
            tenant_client = tenant_mgt.auth_for_tenant(tenant_id)
            custom_token = tenant_client.create_custom_token(
                uid=uid,
                developer_claims=claims
            )
            return custom_token
        except Exception as e:
            raise ValueError(f"Failed to create custom token: {str(e)}")


# Global Firebase auth service instance
firebase_auth_service = FirebaseAuthService()
