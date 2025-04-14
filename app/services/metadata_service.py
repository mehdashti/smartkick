# app/services/metadata_service.py

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

# وارد کردن کلاینت API و ریپازیتوری
from app.api_clients import api_football
from app.repositories.timezone_repository import TimezoneRepository
from app.repositories.country_repository import CountryRepository 
from app.models.country import Country 

# خطاهای کلاینت API را هم وارد می کنیم تا بتوانیم مدیریت کنیم (اگر لازم باشد)
# from app.api_clients.errors import APIFootballError # اگر از خطاهای سفارشی استفاده می کردید
# یا Exception های استاندارد را مدیریت می کنیم

logger = logging.getLogger(__name__)

class MetadataService:
    """
    سرویس برای مدیریت داده های متادیتا مانند Timezone ها.
    شامل منطق خواندن از دیتابیس و به‌روزرسانی از API خارجی.
    """

    async def get_timezones_from_db(self, db: AsyncSession) -> List[str]:
        """
        Timezone ها را از دیتابیس محلی بازیابی می کند.

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            لیستی از نام های timezone ذخیره شده.
        """
        logger.info("Fetching timezones from database...")
        repo = TimezoneRepository(db)
        try:
            # فراخوانی متد ریپازیتوری برای گرفتن همه timezone ها
            timezone_objects = await repo.get_all_timezones()
            # تبدیل لیست اشیاء مدل به لیست نام ها
            timezone_names = [tz.name for tz in timezone_objects]
            logger.info(f"Successfully retrieved {len(timezone_names)} timezones from DB.")
            return timezone_names
        except Exception as e:
            logger.exception("Failed to retrieve timezones from database.")
            # خطا را دوباره raise کن تا روتر آن را مدیریت کند
            raise Exception("Database error occurred while fetching timezones.") from e

    async def update_timezones_from_api(self, db: AsyncSession) -> int:
        """
        Timezone ها را از API خارجی (API-Football) دریافت کرده و
        کل لیست timezone های موجود در دیتابیس را با آن جایگزین می کند.

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            تعداد timezone هایی که با موفقیت در دیتابیس ذخیره شدند.

        Raises:
            Exception: اگر خطایی در ارتباط با API خارجی یا نوشتن در دیتابیس رخ دهد.
                       (این خطا توسط روتر ادمین گرفته و به HTTPException تبدیل می شود)
        """
        logger.info("Starting timezone update process from API...")
        repo = TimezoneRepository(db)
        fetched_count = 0
        try:
            # 1. دریافت لیست timezone ها از API خارجی
            logger.debug("Fetching timezones from external API...")
            timezone_names_from_api = await api_football.fetch_timezones_from_api()

            # بررسی نتیجه API Client
            if timezone_names_from_api is None or not isinstance(timezone_names_from_api, list):
                # اگر API Client به جای لیست یا خطا، None یا نوع دیگری برگرداند (نباید اتفاق بیفتد)
                logger.error("Invalid data received from API client (expected list of strings).")
                # یک خطای داخلی در نظر می گیریم
                raise Exception("Internal Error: Invalid data format received from API client.")

            if not timezone_names_from_api:
                logger.warning("Received empty list of timezones from API. No update performed.")
                return 0 # هیچ آپدیتی انجام نشد

            logger.debug(f"Fetched {len(timezone_names_from_api)} timezones from API.")

            # 2. جایگزینی داده ها در دیتابیس توسط ریپازیتوری
            logger.debug("Replacing all timezones in the database...")
            # ---> فراخوانی متد صحیح ریپازیتوری <---
            fetched_count = await repo.replace_all_timezones(timezone_names_from_api) # نام متد اصلاح شد
            logger.info(f"Successfully updated timezones in DB. {fetched_count} timezones stored.")
            return fetched_count

        except (ValueError, LookupError, ConnectionError, TimeoutError, Exception) as e:
            # گرفتن تمام خطاهای احتمالی از API Client یا خطاهای پایگاه داده از Repository
            logger.exception(f"Failed to update timezones from API: {type(e).__name__}")
            # خطا را دوباره raise کن تا اندپوینت ادمین آن را به کاربر (ادمین) گزارش دهد
            # لایه روتر مسئول تبدیل این خطا به HTTPException 500 یا 503 خواهد بود.
            raise e


    async def get_countries_from_db(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """کشورها را از دیتابیس محلی بازیابی می کند."""
        logger.info("Fetching countries from database...")
        repo = CountryRepository(db)
        try:
            countries_objects = await repo.get_all_countries()
            # تبدیل لیست اشیاء مدل به لیست دیکشنری ها برای API response
            # (بهتر است از مدل Pydantic استفاده شود)
            countries_list = [
                {"id": c.id, "name": c.name, "code": c.code, "flag": c.flag}
                for c in countries_objects
            ]
            logger.info(f"Successfully retrieved {len(countries_list)} countries from DB.")
            return countries_list
        except Exception as e:
            logger.exception("Failed to retrieve countries from database.")
            raise Exception("Database error occurred while fetching countries.") from e

    async def update_countries_from_api(self, db: AsyncSession) -> int:
        """
        کشورها را از API خارجی دریافت کرده و در دیتابیس Upsert می کند.
        """
        logger.info("Starting country update process from API...")
        repo = CountryRepository(db)
        processed_count = 0
        try:
            # 1. Fetch from API
            logger.debug("Fetching countries from external API...")
            countries_data_from_api = await api_football.fetch_countries_from_api()

            if not countries_data_from_api:
                logger.warning("Received empty or invalid list of countries from API. No update performed.")
                return 0

            # ---> شروع: اعمال منطق خاص برای کریمه <---
            processed_countries_data: List[Dict[str, Any]] = []
            for country_data in countries_data_from_api:
                # اطمینان از وجود کلیدهای لازم قبل از دسترسی
                country_name = country_data.get("name")
                country_code = country_data.get("code")

                if country_name == "Crimea":
                    logger.info("Applying special case for Crimea: Setting code to UA-CR")
                    # کد را به UA-CR تغییر می دهیم
                    country_data["code"] = "UA-CR"
                    # مطمئن شوید که سایر فیلدها هم در صورت نیاز تنظیم شوند
                    # country_data["name"] = "Crimea (UA)" # مثال: تغییر نام برای وضوح بیشتر (اختیاری)

                # فقط کشورهایی را اضافه کن که حداقل نام و کد معتبر دارند
                if isinstance(country_name, str) and country_name and isinstance(country_code, str) and country_code:
                     processed_countries_data.append(country_data)
                else:
                     logger.warning(f"Skipping invalid country data: {country_data}")

            # ---> پایان: اعمال منطق خاص <---


            # 2. Upsert data in DB using Repository
            logger.debug(f"Upserting {len(countries_data_from_api)} countries into the database...")
            processed_count = await repo.bulk_upsert_countries(countries_data_from_api)
            logger.info(f"Country update process finished. Processed approximately {processed_count} countries.")
            return processed_count

        except Exception as e:
            logger.exception(f"Failed to update countries from API: {type(e).__name__}")
            raise e # خطا را به روتر منتقل کن

# --- نمونه سازی یا Depends (اختیاری) ---
# دیگر نیازی به نمونه سازی سراسری نیست اگر در روترها نمونه سازی می کنید
# metadata_service_instance = MetadataService()
# def get_metadata_service():
#     return metadata_service_instance