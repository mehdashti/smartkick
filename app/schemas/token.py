# app/schemas/token.py
from pydantic import BaseModel, Field
from typing import List, Optional

class Token(BaseModel):
    """Schema for the login response, containing the access token."""
    access_token: str = Field(..., description="JWT Access Token")
    token_type: str = Field(default="bearer", description="Type of the token")

class TokenPayload(BaseModel):
    """
    Schema representing the data encoded within the JWT payload (standard claims).
    You might add custom claims like 'role' here if needed during creation,
    but often role is checked against the DB after decoding 'sub'.
    """
    sub: Optional[str] = Field(None, description="Subject of the token (usually username or user ID)")
    exp: Optional[int] = Field(None, description="Expiration time (Unix timestamp)")
    iat: Optional[int] = Field(None, description="Issued at time (Unix timestamp)")
    # --- Custom Claims (Add if you encode them directly) ---
    role: Optional[str] = Field(None, description="User role")
    # scopes: List[str] = [] # Example for fine-grained permissions

# --- TokenData (for internal use after decoding) ---
class TokenData(BaseModel):
    """Schema for holding data extracted *after* decoding and verifying the token."""
    username: Optional[str] = None
    role: Optional[str] = None
    scopes: List[str] = []