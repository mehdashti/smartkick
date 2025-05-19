# app/core/database.py
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    async_sessionmaker, 
    AsyncSession
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from typing import AsyncGenerator

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    """
    pass

# تنظیمات موتور async
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_ECHO,
)

# ساخت sessionmaker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# متد برای ایجاد یک AsyncSession
async def async_session() -> AsyncSession:
    """
    ایجاد و بازگرداندن یک AsyncSession.
    """
    return AsyncSessionLocal()

# Dependency برای FastAPI
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: Provides an AsyncSession for the request.
    """
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()