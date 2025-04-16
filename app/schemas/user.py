# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

# --- Base Schema ---
class UserBase(BaseModel):
    """Common base fields for User schemas."""
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$", description="Unique username (alphanumeric and underscore only)")
    email: EmailStr = Field(..., description="User's unique email address")
    full_name: Optional[str] = Field(None, max_length=150, description="User's full name")
    avatar_url: Optional[str] = Field(None, max_length=255, description="URL to user's profile picture")

# --- Schema for Creation ---
class UserCreate(UserBase):
    """Schema used for creating a new user. Requires password."""
    password: str = Field(..., min_length=8, description="User's password (will be hashed)")
    role: str = Field(default="user", pattern="^(user|admin|moderator)$", description="User role") # ادمین‌ها باید نقش را تعیین کنند

# --- Schema for Update (by User) ---
class UserUpdate(BaseModel):
    """Schema for user updating their own profile (limited fields)."""
    email: Optional[EmailStr] = Field(None, description="New email address (might require re-verification)")
    full_name: Optional[str] = Field(None, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=255)
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences as a JSON object")
    # Password update should likely be a separate endpoint

# --- Schema for Update (by Admin) ---
class UserUpdateAdmin(UserUpdate):
    """Schema for admin updating a user's profile (more fields)."""
    username: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    role: Optional[str] = Field(None, pattern="^(user|admin|moderator)$")
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None # Admin can manually verify

# --- Schema for Output (Public Profile) ---
class UserPublic(UserBase):
    """Schema for representing a user publicly (excluding sensitive info)."""
    user_id: int = Field(..., description="User's unique ID")
    role: str = Field(..., description="User's role")
    is_active: bool = Field(..., description="Account status")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode

# --- Schema for Internal Use (includes potentially sensitive info) ---
class UserInDB(UserPublic):
    """Schema representing the full user data as stored in DB (for internal use)."""
    hashed_password: str = Field(..., description="The hashed password (internal only)")
    is_verified: bool
    preferences: Optional[Dict[str, Any]] = None
    last_login_at: Optional[datetime] = None
    updated_at: datetime

    # ORM mode already inherited from UserPublic