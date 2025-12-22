from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from infrastructure.auth import get_auth_provider


# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> Dict[str, Any]:
    """
    Get current user from ID token (via generic AuthProvider)
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Decoded token with user information
        
    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Verify ID token via generic provider
        auth_provider = get_auth_provider()
        decoded_token = await auth_provider.verify_id_token(credentials.credentials)
        return decoded_token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# async def require_auth(request: Request) -> Dict[str, Any]:
#     """
#     Require authentication (backward compatible wrapper)
    
#     Args:
#         request: FastAPI request
        
#     Returns:
#         Decoded token data
#     """
#     auth_header = request.headers.get("Authorization")
    
#     if not auth_header or not auth_header.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Not authenticated"
#         )
    
#     token = auth_header.split(" ")[1]
    
#     try:
#         decoded_token = await firebase_auth_service.verify_id_token(token)
#         return decoded_token
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=str(e)
#         )
