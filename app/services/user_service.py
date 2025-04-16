# app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.repositories.user_repository import UserRepository
# --- استفاده از مدل و اسکیمای جدید ---
from app.models import User as DBUser
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password # verify هم لازم است؟ (شاید برای تغییر رمز)

logger = logging.getLogger(__name__)

class UserService:

    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[DBUser]:
        user_repo = UserRepository(db)
        return await user_repo.get_user_by_username(username)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[DBUser]:
         user_repo = UserRepository(db)
         return await user_repo.get_user_by_email(email)

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> DBUser:
        user_repo = UserRepository(db)
        # بررسی عدم وجود کاربر با نام کاربری یا ایمیل مشابه (مهم!)
        existing_user = await self.get_user_by_username(db, user_in.username)
        if existing_user:
            logger.warning(f"Username '{user_in.username}' already exists.")
            # اینجا می‌توانید خطای خاصی raise کنید یا None برگردانید
            raise ValueError(f"Username '{user_in.username}' is already registered.")
        existing_email = await self.get_user_by_email(db, user_in.email)
        if existing_email:
            logger.warning(f"Email '{user_in.email}' already exists.")
            raise ValueError(f"Email '{user_in.email}' is already registered.")

        # هش کردن رمز عبور
        hashed_password = get_password_hash(user_in.password)
        # ساخت دیکشنری داده برای ریپازیتوری
        user_data = user_in.model_dump(exclude={"password"}) # رمز ساده حذف شود
        user_data["hashed_password"] = hashed_password # هش اضافه شود

        logger.info(f"Attempting to create user '{user_in.username}' via repository.")
        db_user = await user_repo.create_user(user_data=user_data)
        return db_user

    # ... سایر متدهای سرویس (مثل آپدیت، فعال/غیرفعال کردن و ...) ...