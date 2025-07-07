from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()


class AuthService:
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Authenticate user with username and password"""
        # For now, use hardcoded admin credentials
        # In production, this should check against a database
        if username == settings.admin_username and password == settings.admin_password:
            return True
        return False
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                return None
            return payload
        except JWTError:
            return None
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """Get current user from JWT token"""
        token = credentials.credentials
        payload = self.verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    
    def authenticate_basic_auth(self, username: str, password: str) -> bool:
        """Authenticate using basic auth for system-to-system calls"""
        return self.authenticate_user(username, password)


# Global instance
auth_service = AuthService()


# Dependency for JWT authentication
def get_current_user_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency for JWT authentication"""
    return auth_service.get_current_user(credentials)


# Dependency for basic authentication
def get_current_user_basic(username: str, password: str) -> bool:
    """Dependency for basic authentication"""
    return auth_service.authenticate_basic_auth(username, password) 