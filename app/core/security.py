# app/core/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import User  # فرض بر این است که مدل User وجود دارد
from app.repositories.user_repository import UserRepository  # فرض بر این است که ریپازیتوری User وجود دارد
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db_session

# --- Password Hashing ---
# استفاده از bcrypt به عنوان scheme اصلی
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """بررسی مطابقت رمز عبور ساده با هش ذخیره شده"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """ایجاد هش bcrypt برای رمز عبور"""
    return pwd_context.hash(password)

# --- JWT Handling ---
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """ایجاد توکن دسترسی JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # استفاده از مقدار پیش‌فرض از تنظیمات
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    # زمان صدور توکن (اختیاری ولی مفید)
    to_encode.update({"iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    """
    اعتبارسنجی و دیکود کردن توکن JWT.
    در صورت موفقیت payload را برمی‌گرداند، در غیر این صورت None.
    """
    try:
        # امضا، تاریخ انقضا و الگوریتم را بررسی می‌کند
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        print(f"JWT Error: {e}") # لاگ کردن خطا برای دیباگ
        return None

# تنظیم OAuth2 برای دریافت توکن
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db_session)
) -> User:
    """
    دریافت کاربر فعلی از توکن JWT.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    بررسی می‌کند که آیا کاربر فعلی ادمین است یا خیر.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required admin privileges.",
        )
    return current_user

async def get_current_active_user(
    token: str,
    db: AsyncSession = Depends(get_async_db_session)
) -> User:
    """
    دریافت کاربر فعلی از توکن JWT و بررسی فعال بودن کاربر.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )

    return user