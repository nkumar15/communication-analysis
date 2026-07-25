
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AuthProvider(ABC):
    """Abstract base class for authentication providers"""
    
    @abstractmethod
    def initialize(self):
        """Initialize the provider SDK"""
        pass

    @abstractmethod
    async def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify an ID token and return claims
        
        Args:
            id_token: The token string to verify
            
        Returns:
            Dict containing token claims
            
        Raises:
            ValueError: If token is invalid
        """
        pass

    @abstractmethod
    def get_user_info(self, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standard user info from decoded token
        
        Args:
            decoded_token: The decoded token claims
            
        Returns:
            Dict with keys: firebase_uid, email, name, email_verified, firebase_tenant_id
        """
        pass

    @abstractmethod
    def create_custom_token(self, uid: str, tenant_id: str, claims: Optional[Dict[str, Any]] = None) -> bytes:
        """
        Create a signed custom token
        
        Args:
            uid: User ID
            tenant_id: Tenant ID
            claims: Optional custom claims
            
        Returns:
            Encoded token as bytes
        """
        pass
