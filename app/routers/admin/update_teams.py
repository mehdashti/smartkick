# app/routers/admin/update_teams.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from pydantic import BaseModel
import logging
from typing import List

# وابستگی‌ها و سرویس‌ها
from app.routers.dependencies import require_admin_user, DBSession, AdminUser
from app.services.team_service import TeamService

# مدل پاسخ را کمی تغییر می‌دهیم تا لیست خطاها را هم شامل شود
class UpdateAllResponse(BaseModel):
    message: str
    total_count: int
    failed_countries: List[str] = []

# مدل پاسخ قبلی برای تک کشور
class UpdateSingleResponse(BaseModel):
    message: str
    count: int


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/teams",
    tags=["Admin - Teams"],
    dependencies=[Depends(require_admin_user)] # اعمال امنیت در سطح روتر
)

# --- استفاده از Union در response_model برای مشخص کردن پاسخ‌های ممکن ---
# from typing import Union # اگر بخواهید response_model را دقیق‌تر کنید

@router.post(
    "/update-by-country/{country_name}",
    status_code=status.HTTP_200_OK,
    summary="Fetch and Update Teams & Venues by Country or All Countries",
    description=(
        "Retrieves the latest list of teams and venues from API-Football "
        "and upserts them into the local database. \n\n"
        "Use a specific country name (e.g., 'Iran', 'England') or use "
        "'allcountries' (case-insensitive) to update for all countries in the DB. "
        "Requires Admin privileges."
    ),
    response_description="Confirmation message and the approximate number of entries processed. If 'allcountries' is used, also returns a list of countries where updates failed.",
    # response_model=Union[UpdateSingleResponse, UpdateAllResponse] # <--- مشخص کردن نوع پاسخ های ممکن
    # یا به صورت ساده تر فعلا از UpdateAllResponse برای هر دو استفاده کنیم و count را 0 بگذاریم اگر تک بود
    response_model=UpdateAllResponse # <--- موقتا از این برای سادگی استفاده می‌کنیم
)

async def trigger_team_update_by_country(
    *, # باعث می‌شود پارامترهای بعدی فقط با نام قابل ارسال باشند
    db: DBSession,
    admin_user: AdminUser, # گرفتن کاربر ادمین برای لاگینگ (اختیاری)
    country_name: str = Path(..., title="Country Name", description="The name of the country to fetch teams for (e.g., 'Iran', 'England')")
) -> UpdateAllResponse: 
    
    """
    Endpoint to manually trigger the update of team and venue data.
    Can process a single country or all countries using 'allcountries'.
    """
    team_service = TeamService()
    # مقایسه بدون حساسیت به بزرگی و کوچکی حروف
    process_all = country_name.lower() == "allcountries"

    if process_all:
        logger.info(f"Admin request received from '{admin_user.username}': Trigger team/venue update for ALL countries.")
        target_description = "all countries"
    else:
        logger.info(f"Admin request received from '{admin_user.username}': Trigger team/venue update for country '{country_name}'.")
        target_description = f"country '{country_name}'"

    try:
        if process_all:
            # --- فراخوانی متد برای همه کشورها ---
            total_count, failed_list = await team_service.update_teams_for_all_countries(db=db)
            msg = f"Team/Venue update process for ALL countries finished."
            if failed_list:
                msg += f" Updates failed for: {', '.join(failed_list)}."
            return UpdateAllResponse(message=msg, total_count=total_count, failed_countries=failed_list)
        else:
            # --- فراخوانی متد برای تک کشور ---
            processed_count = await team_service.update_teams_by_country(db=db, country_name=country_name)
            logger.info(f"Team/Venue update process completed via admin endpoint for {target_description}. Count: {processed_count}")
            # با فرمت UpdateAllResponse برمی‌گردانیم
            return UpdateAllResponse(
                message=f"Team/Venue update process for {target_description} finished successfully.",
                total_count=processed_count, # از total_count استفاده می‌کنیم
                failed_countries=[] # لیست خطاها خالی است
            )

    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API communication error during team update for {target_description}: {api_error}", exc_info=False)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to the external API or request timed out while processing {target_description}: {type(api_error).__name__}"
        )
    except LookupError as data_error:
        logger.warning(f"Data lookup error during team update for {target_description}: {data_error}")
        # این خطا معمولا برای تک کشور معنی دارد
        if not process_all:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Data not found for {target_description}: {data_error}"
            )
        else: # اگر در حین پردازش همه کشورها رخ دهد (مثلا در گرفتن لیست اولیه)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Lookup error during 'all countries' process: {data_error}"
             )
    except ValueError as validation_error:
        logger.error(f"Data processing or validation error during team update for {target_description}: {validation_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data processing error for {target_description}: {validation_error}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error occurred during admin-triggered team update for {target_description}.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred processing {target_description}: {type(e).__name__}"
        )