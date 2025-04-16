# app/repositories/user_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, Sequence # برای get_users
import logging

# --- استفاده از مدل SQLAlchemy جدید ---
from app.models import User as DBUser

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_user_by_username(self, username: str) -> Optional[DBUser]:
        logger.debug(f"Querying DB for user with username: {username}")
        query = select(DBUser).filter(DBUser.username == username)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_user_by_email(self, email: str) -> Optional[DBUser]:
        logger.debug(f"Querying DB for user with email: {email}")
        query = select(DBUser).filter(DBUser.email == email)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> Optional[DBUser]:
        logger.debug(f"Querying DB for user with ID: {user_id}")
        query = select(DBUser).filter(DBUser.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def create_user(self, user_data: dict) -> DBUser:
         logger.debug(f"Creating new user in DB: {user_data.get('username')}")
         # user_data باید شامل hashed_password باشد
         db_user = DBUser(**user_data)
         self.db.add(db_user)
         await self.db.flush() # برای گرفتن ID قبل از commit (اگر لازم باشد)
         await self.db.refresh(db_user)
         logger.info(f"User '{db_user.username}' added to session (ID: {db_user.user_id}).")
         return db_user

    async def get_users(self, skip: int = 0, limit: int = 100) -> Sequence[DBUser]:
         """دریافت لیستی از کاربران با分页"""
         logger.debug(f"Querying DB for users: skip={skip}, limit={limit}")
         query = select(DBUser).offset(skip).limit(limit).order_by(DBUser.user_id)
         result = await self.db.execute(query)
         return result.scalars().all()

    # ... می‌توانید متدهای آپدیت و حذف را هم اضافه کنید ...
    # async def update_user(self, user: DBUser, update_data: dict) -> DBUser: ...
    # async def delete_user(self, user: DBUser) -> None: ...