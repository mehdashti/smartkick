# app/routers/admin/update_leagues.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging
import httpx

from app.core.database import get_async_db_session
from app.services.league_service import LeagueService
# --- فعال کردن وابستگی امنیتی ---
from app.routers.dependencies import require_admin_user, DBSession, AdminUser # Import AdminUser too

logger = logging.getLogger(__name__)

class UpdateResponse(BaseModel):
    message: str
    count: int

router = APIRouter(
    prefix="/admin/leagues",
    tags=["Admin - Leagues"],
    # --- فعال کردن امنیت در سطح روتر ---
    dependencies=[Depends(require_admin_user)]
)

@router.post(
    "/update-leagues",
    # ... (بقیه دکوراتور بدون تغییر) ...
    response_model=UpdateResponse
)
async def trigger_league_update(
    db: DBSession, # استفاده از Type hint
    # (اختیاری) می‌توانید کاربر ادمین را هم بگیرید اگر لازمش دارید
    # admin_user: AdminUser
) -> UpdateResponse:
    # حالا این اندپوینت فقط توسط ادمین‌های معتبر قابل دسترسی است
    # logger.info(f"Admin request received from user '{admin_user.username}': Trigger league update.")
    logger.info("Admin request received: Trigger league update.")
    league_service = LeagueService() # ساخت سرویس

    try:
        # حالا که وابستگی get_async_db_session تراکنش را مدیریت می‌کند،
        # نیازی به begin/commit/rollback در سرویس یا ریپازیتوری نیست.
        processed_count = await league_service.update_leagues_from_api(db)
        logger.info(f"League update process completed via admin endpoint. Count: {processed_count}")
        return UpdateResponse(message="League update process finished successfully.", count=processed_count)
    # ... (بخش except بدون تغییر) ...
    except (httpx.RequestError, httpx.TimeoutException, ConnectionError, TimeoutError) as api_error:
         logger.error(f"API or Network error during league update: {api_error}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail=f"Could not connect to the external API or request timed out: {type(api_error).__name__}"
         )
    except ValueError as validation_error:
         logger.error(f"Data processing error during league update: {validation_error}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"Data processing error: {validation_error}"
         )
    except Exception as e:
         logger.exception("Unexpected error occurred during admin-triggered league update.")
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail=f"An unexpected internal error occurred: {type(e).__name__}"
         )