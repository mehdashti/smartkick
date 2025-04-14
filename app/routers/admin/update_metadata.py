# app/routers/admin/update_metadata.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

# وارد کردن وابستگی‌ها و سرویس‌های لازم
from app.core.database import get_async_db_session
from app.services.metadata_service import MetadataService

# ---> TODO: وارد کردن و فعال سازی وابستگی امنیتی برای ادمین <---
# مثال: from ..dependencies import require_admin_user

logger = logging.getLogger(__name__)

# ایجاد روتر مخصوص این بخش ادمین
router = APIRouter(
    prefix="/admin/metadata",  # پیشوند مشخص برای اندپوینت‌های متادیتا در بخش ادمین
    tags=["Admin - Metadata"],  # تگ برای گروه بندی در مستندات
    # dependencies=[Depends(require_admin_user)] # <--- اعمال امنیت در سطح روتر
)

@router.post(
    "/update-timezones", # مسیر کامل: /admin/metadata/update-timezones
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Timezones",
    description="Retrieves the latest list of timezones from the external API (API-Football) and updates the local database, replacing all existing entries.",
    response_description="Confirmation message and the number of timezones updated."
)
async def trigger_timezone_update(
    db: AsyncSession = Depends(get_async_db_session) # تزریق session دیتابیس
):
    """
    Endpoint to manually trigger the update of timezones data.
    Fetches from API-Football and stores in the database.
    Requires Admin privileges.
    """
    logger.info("Admin request received: Trigger timezone update.")

    # ایجاد نمونه از سرویس
    metadata_service = MetadataService()

    try:
        # فراخوانی متد سرویس که مسئول کل فرآیند است
        updated_count = await metadata_service.update_timezones_from_api(db)

        logger.info(f"Timezone update process completed via admin endpoint. Count: {updated_count}")
        return {
            "message": "Timezone update process finished successfully.",
            "timezones_updated": updated_count
        }
    except Exception as e:
        # گرفتن هرگونه خطای پیش بینی نشده از سرویس (که شامل خطاهای کلاینت و ریپازیتوری هم می شود)
        logger.exception("Error occurred during admin-triggered timezone update.") # لاگ کردن با traceback
        # برگرداندن خطای عمومی سرور به ادمین
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during timezone update: {type(e).__name__}"
        )


@router.post(
    "/update-countries",
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Countries",
    description="Retrieves the latest list of countries from API-Football and upserts them into the local database.",
    response_description="Confirmation message and the approximate number of countries processed."
)
async def trigger_country_update(
    db: AsyncSession = Depends(get_async_db_session)
):
    """Triggers the update process for countries."""
    logger.info("Admin endpoint triggered: POST /admin/metadata/update-countries")
    service = MetadataService()
    try:
        count = await service.update_countries_from_api(db)
        return {"message": "Country update process finished.", "countries_processed": count}
    except Exception as e:
        logger.exception("Error during admin-triggered country update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update countries: {type(e).__name__}"
        )

# می توانید اندپوینت های دیگری برای مدیریت متادیتا اینجا اضافه کنید