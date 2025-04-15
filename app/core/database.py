# app/core/database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    async_sessionmaker, 
    AsyncSession,
    AsyncAttrs
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from typing import AsyncGenerator

class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all SQLAlchemy models with async attributes support.
    """
    pass

# تنظیمات موتور async با پارامترهای بهینه‌شده
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.SQL_ECHO  # تنظیم از طریق env var
)

# ساخت sessionmaker با تنظیمات پیشرفته
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
#    future=True
)

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: Provides an AsyncSession with the entire request
    scoped within a single transaction managed by this dependency.
    """
    async with AsyncSessionLocal() as session: # مدیریت ایجاد و بسته شدن session
        # --- شروع تراکنش قبل از yield ---
        async with session.begin(): # مدیریت commit و rollback خودکار
            try:
                # Session با تراکنش فعال در اختیار قرار می گیرد
                yield session
                # در صورت موفقیت و خروج عادی از بلاک with، commit خودکار انجام می شود
            except Exception:
                # در صورت بروز خطا، rollback خودکار توسط session.begin() انجام می شود
                # و خطا به بالا propagate می شود تا FastAPI آن را مدیریت کند
                raise
        # --- پایان بلاک session.begin() ---
    # --- پایان بلاک AsyncSessionLocal() -> session بسته می شود ---