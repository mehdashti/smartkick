# app/core/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.core.config import settings

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