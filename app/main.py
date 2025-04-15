# app/main.py
import logging
import sys
from contextlib import asynccontextmanager # <--- وارد کردن context manager
from fastapi import FastAPI
from app.routers import players, teams#, metadata # ... و سایر روترها
from app.routers.admin import update_metadata as admin_metadata_router
from app.routers.admin import update_leagues as admin_leagues_router 


# --- تنظیمات لاگینگ (بدون تغییر) ---
log_level = logging.INFO
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(logging.Formatter(log_format))
root_logger = logging.getLogger()
root_logger.setLevel(log_level)
root_logger.addHandler(stream_handler)
# logging.getLogger("httpx").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ---> شروع تغییر: استفاده از lifespan <---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """مدیریت رویدادهای شروع و پایان برنامه."""
    # کدی که هنگام شروع اجرا می شود
    logger.info("Application startup via lifespan.")
    # مثال: ایجاد connection pool دیتابیس، بارگذاری مدل ها و ...

    yield # اجرای برنامه اصلی در اینجا اتفاق می افتد

    # کدی که هنگام خاموش شدن اجرا می شود
    logger.info("Application shutdown via lifespan.")
    # مثال: بستن connection pool ها، آزادسازی منابع

# ---> پایان تغییر <---


# --- ساخت برنامه FastAPI با lifespan ---
app = FastAPI(
    title="Football Data API",
    description="API for fetching and serving football data.", # اضافه کردن توضیحات خوب است
    version="0.1.0",
    lifespan=lifespan # <--- اتصال lifespan manager
)


# ---> حذف دکوراتورها و توابع on_event قدیمی <---
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup complete.") # منتقل شد به lifespan

# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown.") # منتقل شد به lifespan


# --- اتصال روترهای ادمین ---
app.include_router(admin_metadata_router.router)
app.include_router(admin_leagues_router.router)  # <--- ثبت روتر ادمین
# ... (سایر روترهای ادمین که در آینده اضافه می شوند) ...

# --- اتصال روترها (بدون تغییر) ---
app.include_router(players.router)
app.include_router(teams.router)
#app.include_router(metadata.router)


# --- اندپوینت ریشه (بدون تغییر) ---
@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the Football Data API!"}

