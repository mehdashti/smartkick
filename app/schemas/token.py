# app/schemas/token.py
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime
from pydantic.alias_generators import to_camel
from enum import Enum

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        #alias_generator=to_camel,
        extra="ignore"
    )

class TokenType(str, Enum):
    """Enum for token types"""
    BEARER = "bearer"
    REFRESH = "refresh"

class Token(APIModel):
    """Schema for authentication token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: TokenType = Field(default=TokenType.BEARER, description="Token type")
    expires_in: Optional[int] = Field(None, description="Expiration time in seconds")

class TokenPayload(APIModel):
    """Schema representing JWT payload claims"""
    sub: str = Field(..., description="Subject identifier (user ID)")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: Optional[str] = Field(None, description="Token unique identifier")
    role: Optional[str] = Field(None, description="User role")
    scopes: List[str] = Field(default_factory=list, description="Token permissions")

class TokenData(APIModel):
    """Schema for internal token data after verification"""
    user_id: str = Field(..., description="Authenticated user ID")
    username: Optional[str] = Field(None, description="Username")
    role: Optional[str] = Field(None, description="User role")
    scopes: List[str] = Field(default_factory=list, description="Authorized permissions")
    expires_at: Optional[datetime] = Field(None, description="Token expiration datetime")

class RefreshTokenRequest(APIModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., description="Valid refresh token")

class TokenRevocationRequest(APIModel):
    """Schema for token revocation request"""
    token: str = Field(..., description="Token to revoke")
    token_type_hint: Optional[str] = Field(None, description="Type of token to revoke")

class TokenValidationResponse(APIModel):
    """Schema for token validation response"""
    is_valid: bool = Field(..., description="Token validity status")
    is_expired: bool = Field(..., description="Token expiration status")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    scopes: List[str] = Field(default_factory=list, description="Token permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")