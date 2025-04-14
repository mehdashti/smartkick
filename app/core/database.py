# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings # برای خواندن DATABASE_URL از .env

# ساخت موتور آسنکرون SQLAlchemy
# URL باید فرمت async داشته باشد (e.g., postgresql+asyncpg://...)
async_engine = create_async_engine(
    settings.DATABASE_URL,
    # echo=True, # برای دیدن کوئری های SQL در لاگ (برای دیباگ)
    pool_pre_ping=True # بررسی اتصال قبل از استفاده از کانکشن در پول
)

# ساخت sessionmaker آسنکرون
# expire_on_commit=False معمولا برای استفاده با FastAPI توصیه می شود
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ---> تعریف Base مدل <---
# تمام مدل های SQLAlchemy شما باید از این Base ارث بری کنند
Base = declarative_base()

# --- تابع Dependency برای گرفتن Session در روترها ---
async def get_async_db_session() -> AsyncSession:
    """
    FastAPI dependency that provides an async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # این بخش commit را اختیاری می کند، بهتر است commit در سرویس یا ریپازیتوری باشد
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # session به طور خودکار توسط async with بسته می شود
            pass

# --- (اختیاری) تابع برای ایجاد جداول (برای تست یا شروع اولیه بدون alembic) ---
# async def create_db_and_tables():
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)