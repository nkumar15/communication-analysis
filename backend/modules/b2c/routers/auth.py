"""B2C Authentication Router"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from core.db.session import get_db
from modules.b2c.services.auth_service import auth_service
from modules.b2c.middleware.b2c_auth import get_current_b2c_user
from infrastructure.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/b2c/auth", tags=["B2C Auth"])


# Schemas
class SignupRequest(BaseModel):
    id_token: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    id_token: str


class SignupResponse(BaseModel):
    user: dict
    workspace: dict


class LoginResponse(BaseModel):
    user: dict
    workspaces: list


class UserInfoResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    personal_workspace_id: str | None
    workspaces: list


@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sign up new B2C user
    
    Auto-creates personal workspace
    Requires verified Firebase ID token
    """
    from infrastructure.auth import firebase_auth_service
    
    # Verify Firebase token
    try:
        decoded_token = await firebase_auth_service.verify_id_token(request.id_token)
        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        email_verified = decoded_token.get('email_verified', False)
        
        # DEBUG: Log token claims to debug 403
        logger.info("firebase_token_claims", 
                   uid=firebase_uid, 
                   email=email, 
                   email_verified=email_verified,
                   claims=decoded_token)
        
        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
    except Exception as e:
        logger.error("signup_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Create user + workspace
    result = await auth_service.signup(
        db=db,
        firebase_uid=firebase_uid,
        email=email,
        display_name=request.display_name,
        email_verified=email_verified
    )
    
    await db.commit()
    
    return SignupResponse(**result)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login B2C user
    
    Idempotent: Creates user+workspace on first login if needed
    """
    from infrastructure.auth import firebase_auth_service
    
    # Verify Firebase token
    try:
        decoded_token = await firebase_auth_service.verify_id_token(request.id_token)
        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        email_verified = decoded_token.get('email_verified', False)
        display_name = decoded_token.get('name')
        
        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
    except Exception as e:
        logger.error("login_token_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get or create user
    user = await auth_service.get_or_create_user(
        db=db,
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name,
        email_verified=email_verified
    )
    
    # Get workspaces
    workspaces = await auth_service.get_user_workspaces(db, str(user.id))
    
    await db.commit()
    
    return LoginResponse(
        user={
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "personal_workspace_id": str(user.default_workspace_id) if user.default_workspace_id else None
        },
        workspaces=workspaces
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    current_user: dict = Depends(get_current_b2c_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user info with workspaces"""
    
    # Get workspaces
    workspaces = await auth_service.get_user_workspaces(db, str(current_user['id']))
    
    return UserInfoResponse(
        id=str(current_user['id']),
        email=current_user['email'],
        display_name=current_user.get('display_name'),
        personal_workspace_id=str(current_user.get('personal_workspace_id')) if current_user.get('personal_workspace_id') else None,
        workspaces=workspaces
    )
