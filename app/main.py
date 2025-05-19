# app/main.py
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
import app.schemas

# --- روترهای ادمین ---
from app.routers.admin import update_metadata as admin_metadata_router
from app.routers.admin import update_leagues as admin_leagues_router
from app.routers.admin import update_teams as admin_teams_router
from app.routers.admin import update_venues as admin_venues_router
from app.routers.admin import update_players as admin_players_router
from app.routers.admin import update_player_stats as admin_player_stats_router
from app.routers.admin import update_fixtures as update_fixtures_router
from app.routers.admin import task_status as task_status_router

# --- روتر احراز هویت ---
from app.routers import auth # <--- وارد کردن روتر auth

# --- تنظیمات لاگینگ ---
# ... (کد لاگینگ شما بدون تغییر) ...
logger = logging.getLogger(__name__)

# --- Lifespan (اصلاح شده برای Redis) --- # <--- اینجا تغییر می‌کند
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup via lifespan.")
    yield
    logger.info("Application shutdown via lifespan.")

# --- ساخت برنامه FastAPI ---
app = FastAPI(
    title="SmartKick Football API",
    description="API for fetching and serving football data.",
    version="0.1.0",
    lifespan=lifespan # <--- lifespan اصلاح شده به FastAPI داده می‌شود
)

# --- اتصال روترها ---

# 1. روتر احراز هویت
app.include_router(auth.auth_router)

# 2. روترهای ادمین
app.include_router(admin_metadata_router.router)
app.include_router(admin_leagues_router.router)
app.include_router(admin_teams_router.router)
app.include_router(admin_venues_router.router)
app.include_router(admin_players_router.router)
app.include_router(admin_player_stats_router.router)
app.include_router(task_status_router.router)
app.include_router(update_fixtures_router.router)


# 4. روترهای عمومی (اگر دارید)
# app.include_router(players.router, prefix="/public", tags=["Players"])
# app.include_router(teams.router, prefix="/public", tags=["Teams"])

# --- اندپوینت ریشه ---
@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint accessed.")
    return {"message": "Welcome to the SmartKick API!"}

# --- (اختیاری) CORS ---
# ... (اگر نیاز دارید)