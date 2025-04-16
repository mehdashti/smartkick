# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
import logging

from app.core.security import create_access_token, verify_password
# --- استفاده از اسکیماهای جدید ---
from app.schemas.token import Token
from app.schemas.user import UserPublic
# --- استفاده از سرویس کاربر ---
from app.services.user_service import UserService
from app.routers.dependencies import DBSession, CurrentUserPublic, AdminUser, CurrentUser # وارد کردن وابستگی‌ها

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

AuthFormData = Annotated[OAuth2PasswordRequestForm, Depends()]

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: AuthFormData, db: DBSession):
    logger.info(f"Login attempt for user: {form_data.username}")
    user_service = UserService()
    # --- احراز هویت با نام کاربری ---
    user = await user_service.get_user_by_username(db, username=form_data.username)
    # --- یا احراز هویت با ایمیل (اگر ترجیح می‌دهید) ---
    # user = await user_service.get_user_by_email(db, email=form_data.username) # اگر فرم ایمیل می‌گیرد

    login_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed for '{form_data.username}': Incorrect credentials.")
        raise login_exception

    if not user.is_active:
         logger.warning(f"Login failed: User '{form_data.username}' is inactive.")
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # --- به‌روزرسانی زمان آخرین ورود (اختیاری) ---
    # user.last_login_at = func.now() # نیاز به commit دارد که وابستگی get_db انجام می‌دهد
    # await db.merge(user) # یا روش دیگر برای آپدیت

    # ساخت توکن
    access_token_data = {"sub": user.username, "role": user.role} # نقش را هم می‌توان در توکن گذاشت
    access_token = create_access_token(data=access_token_data)
    logger.info(f"Login successful for user: {form_data.username}. Token issued.")

    return Token(access_token=access_token, token_type="bearer")

# اندپوینت مشاهده پروفایل کاربر فعلی
@auth_router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: CurrentUserPublic):
     """Get current logged-in user's public profile."""
     logger.debug(f"'/auth/me' endpoint accessed by user: {current_user.username}")
     return current_user

# (اختیاری) اندپوینت تست ادمین
@auth_router.get("/me/admin-test", response_model=UserPublic)
async def read_admin_me(admin_user: AdminUser): # از AdminUser که مدل DB است استفاده می‌کنیم
    """(Test endpoint) Get current user info if they are an admin."""
    logger.debug(f"'/auth/me/admin-test' accessed by admin: {admin_user.username}")
    # تبدیل به UserPublic قبل از بازگرداندن
    return UserPublic.model_validate(admin_user)