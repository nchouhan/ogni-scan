from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from backend.schemas.auth import LoginRequest, LoginResponse, UserResponse, ErrorResponse
from backend.services.auth_service import auth_service, get_current_user_jwt
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_basic = HTTPBasic()


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    """Login with username and password"""
    try:
        if auth_service.authenticate_user(login_request.username, login_request.password):
            access_token = auth_service.create_access_token(
                data={"sub": login_request.username}
            )
            return LoginResponse(
                access_token=access_token,
                username=login_request.username
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: dict = Depends(get_current_user_jwt)):
    """Get current user information"""
    return UserResponse(username=current_user.get("sub", ""))


@router.post("/basic-auth")
async def basic_auth(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """Basic authentication for system-to-system calls"""
    try:
        if auth_service.authenticate_basic_auth(credentials.username, credentials.password):
            return {"authenticated": True, "username": credentials.username}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
    except Exception as e:
        logger.error(f"Basic auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 