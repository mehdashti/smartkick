# app/main.py
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI

# --- روترهای ادمین ---
from app.routers.admin import update_metadata as admin_metadata_router
from app.routers.admin import update_leagues as admin_leagues_router
from app.routers.admin import update_teams as admin_teams_router 
# ... سایر روترهای ادمین ...

# --- روترهای عمومی ---
from app.routers import players, teams #, metadata
# ... سایر روترهای عمومی ...

# --- روتر احراز هویت ---
from app.routers import auth # <--- وارد کردن روتر auth

# --- تنظیمات لاگینگ (بدون تغییر) ---
# ... (کد لاگینگ شما) ...
logger = logging.getLogger(__name__)

# --- Lifespan (بدون تغییر) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup via lifespan.")
    yield
    logger.info("Application shutdown via lifespan.")

# --- ساخت برنامه FastAPI ---
app = FastAPI(
    title="SmartKick Football API", # <--- نام پروژه شما
    description="API for fetching and serving football data.",
    version="0.1.0",
    lifespan=lifespan
)

# --- اتصال روترها ---

# 1. روتر احراز هویت (معمولاً اولین روتر برای وضوح)
app.include_router(auth.auth_router)

# 2. روترهای ادمین (که وابستگی امنیتی دارند)
# (اگر یک admin_base دارید که بقیه را include می‌کند، فقط آن را ثبت کنید)
# app.include_router(admin_base.admin_router)
# در غیر این صورت، هر کدام را جداگانه ثبت کنید:
app.include_router(admin_metadata_router.router) # فرض وجود وابستگی امنیتی در این روتر
app.include_router(admin_leagues_router.router) # این روتر حالا وابستگی امنیتی دارد
app.include_router(admin_teams_router.router)

# 3. روترهای عمومی
app.include_router(players.router, prefix="/public", tags=["Players"]) # مثال با prefix
app.include_router(teams.router, prefix="/public", tags=["Teams"])
# app.include_router(metadata.router, prefix="/public", tags=["Metadata"])

# --- اندپوینت ریشه ---
@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the SmartKick API!"}

# --- (اختیاری) CORS ---
# from fastapi.middleware.cors import CORSMiddleware
# origins = ["http://localhost:3000"] # آدرس فرانت‌اند شما
# app.add_middleware(...)