from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    message: str = "Login successful"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    is_authenticated: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None 