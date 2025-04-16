# app/models/token.py
from pydantic import BaseModel
from typing import List, Optional

class Token(BaseModel):
    """مدل پاسخ برای اندپوینت لاگین"""
    access_token: str
    token_type: str = "bearer" # همیشه bearer است

class TokenData(BaseModel):
    """مدل داده‌های استخراج شده از payload توکن"""
    username: Optional[str] = None
    role: Optional[str] = None
    scopes: List[str] = [] # برای مدیریت دسترسی دقیق‌تر در آینده