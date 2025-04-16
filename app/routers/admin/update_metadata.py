# app/routers/admin/update_metadata.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel 
import logging
import httpx 

# وارد کردن وابستگی‌ها و سرویس‌های لازم
from app.core.database import get_async_db_session
from app.services.metadata_service import MetadataService
from app.models import Country, Timezone, League # <--- برای استفاده از مدل‌ها

# ---> !!! حتماً این بخش را پیاده‌سازی و فعال کنید !!! <---
# from ..dependencies import require_admin_user # مثال

logger = logging.getLogger(__name__)

# --- تعریف مدل پاسخ برای مستندسازی بهتر ---
class UpdateResponse(BaseModel):
    message: str
    count: int

# ایجاد روتر مخصوص این بخش ادمین
router = APIRouter(
    prefix="/admin/metadata",
    tags=["Admin - Metadata"],
    # dependencies=[Depends(require_admin_user)] # <--- !!! فعال شود !!!
)

@router.post(
    "/update-timezones",
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Timezones",
    description="Retrieves the latest list of timezones from the external API (API-Football) and updates the local database, replacing all existing entries. Requires Admin privileges.",
    response_description="Confirmation message and the number of timezones updated.",
    response_model=UpdateResponse # <--- استفاده از Response Model
)
async def trigger_timezone_update(
    db: AsyncSession = Depends(get_async_db_session)
) -> UpdateResponse: # <--- نوع بازگشتی مشخص شد
    """
    Endpoint to manually trigger the update of timezones data.
    Fetches from API-Football and stores in the database.
    Requires Admin privileges.
    """
    logger.info("Admin request received: Trigger timezone update.")
    metadata_service = MetadataService()

    try:
        updated_count = await metadata_service.update_timezones_from_api(db)
        logger.info(f"Timezone update process completed via admin endpoint. Count: {updated_count}")
        return UpdateResponse(message="Timezone update process finished successfully.", count=updated_count)

    # گرفتن خطاهای احتمالی شبکه یا تایم‌اوت از httpx یا API Client
    except (httpx.RequestError, httpx.TimeoutException, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API or Network error during timezone update: {api_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to the external API or request timed out: {type(api_error).__name__}"
        )
    # گرفتن سایر خطاهای پیش بینی نشده (مثلا خطای دیتابیس از ریپازیتوری)
    except Exception as e:
        logger.exception("Unexpected error occurred during admin-triggered timezone update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {type(e).__name__}"
        )


@router.post(
    "/update-countries",
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Countries",
    description="Retrieves the latest list of countries from API-Football and upserts them into the local database. Requires Admin privileges.",
    response_description="Confirmation message and the approximate number of countries processed.",
    response_model=UpdateResponse # <--- استفاده از Response Model
)
async def trigger_country_update(
    db: AsyncSession = Depends(get_async_db_session)
) -> UpdateResponse: # <--- نوع بازگشتی مشخص شد
    """Triggers the update process for countries. Requires Admin privileges."""
    logger.info("Admin endpoint triggered: POST /admin/metadata/update-countries")
    service = MetadataService()
    try:
        processed_count = await service.update_countries_from_api(db)
        logger.info(f"Country update process completed via admin endpoint. Count: {processed_count}")
        return UpdateResponse(message="Country update process finished.", count=processed_count)

    # گرفتن خطاهای احتمالی شبکه یا تایم‌اوت از httpx یا API Client
    except (httpx.RequestError, httpx.TimeoutException, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API or Network error during country update: {api_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to the external API or request timed out: {type(api_error).__name__}"
        )
    # گرفتن سایر خطاهای پیش بینی نشده
    except Exception as e:
        logger.exception("Unexpected error occurred during admin-triggered country update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred: {type(e).__name__}"
        )