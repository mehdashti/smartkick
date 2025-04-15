# app/routers/admin/update_leagues.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging
import httpx

# وارد کردن وابستگی‌ها و سرویس‌های لازم
from app.core.database import get_async_db_session
from app.services.league_service import LeagueService # سرویس جدید لیگ
# from ..dependencies import require_admin_user # !!! فعال شود !!!

logger = logging.getLogger(__name__)

# مدل پاسخ مشترک (از فایل دیگر کپی شده یا ایمپورت شود)
class UpdateResponse(BaseModel):
    message: str
    count: int

# ایجاد روتر
router = APIRouter(
    prefix="/admin/leagues",
    tags=["Admin - Leagues"],
    # dependencies=[Depends(require_admin_user)] # <--- !!! فعال شود !!!
)

@router.post(
    "/update-leagues",
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Leagues & Seasons",
    description="Retrieves the latest list of leagues and their seasons from API-Football and upserts them into the local database. Requires Admin privileges.",
    response_description="Confirmation message and the approximate number of league/season entries processed.",
    response_model=UpdateResponse
)
async def trigger_league_update(
    db: AsyncSession = Depends(get_async_db_session)
) -> UpdateResponse:
    """
    Endpoint to manually trigger the update of league and season data.
    Fetches from API-Football and stores/updates in the database.
    Requires Admin privileges.
    """
    logger.info("Admin request received: Trigger league update.")
    league_service = LeagueService()

    try:
        processed_count = await league_service.update_leagues_from_api(db)
        logger.info(f"League update process completed via admin endpoint. Count: {processed_count}")
        return UpdateResponse(message="League update process finished successfully.", count=processed_count)

    except (httpx.RequestError, httpx.TimeoutException, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API or Network error during league update: {api_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to the external API or request timed out: {type(api_error).__name__}"
        )
    except ValueError as validation_error: # گرفتن خطاهای احتمالی پردازش داده
        logger.error(f"Data processing error during league update: {validation_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # یا 500 بسته به نوع خطا
            detail=f"Data processing error: {validation_error}"
        )
    except Exception as e: # سایر خطاهای پیش بینی نشده (مثل خطای DB)
        logger.exception("Unexpected error occurred during admin-triggered league update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {type(e).__name__}"
        )