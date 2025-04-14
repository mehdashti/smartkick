# app/routers/metadata.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.services.metadata_service import MetadataService, update_timezones_from_api # سرویس و تابع Depends
from app.api_clients.errors import APIFootballError # برای مدیریت خطای خاص

router = APIRouter(
    prefix="/meta", # یک پیشوند مناسب برای اندپوینت‌های عمومی/متادیتا
    tags=["Metadata"] # گروه بندی در مستندات /docs
)

@router.get(
    "/timezones",
    response_model=List[str], # مهم: مشخص کردن مدل پاسخ برای مستندات و اعتبارسنجی خروجی
    summary="دریافت لیست Timezone های پشتیبانی شده",
    description="لیست تمام Timezone هایی که توسط API-Football پشتیبانی می‌شوند را برمی‌گرداند."
)
async def get_supported_timezones(
    service: MetadataService = Depends(get_metadata_service) # تزریق سرویس
):
    """
    اندپوینت برای دریافت لیست timezone ها.
    """
    print("[Router] Received request for /meta/timezones")
    try:
        timezones = await service.get_timezones()
        print(f"[Router] Returning {len(timezones)} timezones to client.")
        return timezones
    except APIFootballError as e:
        # خطای مشخصی که از لایه سرویس یا کلاینت می‌آید
        print(f"[Router] APIFootballError occurred: {e}")
        raise HTTPException(
            status_code=503, # Service Unavailable (چون به سرویس خارجی وابسته است)
            detail=f"خطا در دریافت اطلاعات از سرویس خارجی: {e}"
        )
    except Exception as e:
        # خطاهای پیش‌بینی نشده دیگر
        print(f"[Router] Unexpected error: {e}")
        raise HTTPException(
            status_code=500, # Internal Server Error
            detail="یک خطای داخلی در سرور رخ داده است."
        )