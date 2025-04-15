# app/services/metadata_service.py

from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

# وارد کردن کلاینت API و ریپازیتوری
from app.api_clients import api_football
from app.repositories.timezone_repository import TimezoneRepository
from app.repositories.country_repository import CountryRepository
from app.models import Country, Timezone, League

# --- وارد کردن اسکیماها ---
from app.schemas.timezone import TimezoneOut # <-- جدید
from app.schemas.country import CountryOut   # <-- جدید
# اگر ریپازیتوری انتظار اسکیما برای ورودی داشت، آنها را هم وارد می کردیم:
# from app.schemas.timezone import TimezoneCreate
# from app.schemas.country import CountryCreate

# (خطاهای کلاینت API مانند قبل)

logger = logging.getLogger(__name__)

class MetadataService:
    """
    سرویس برای مدیریت داده های متادیتا مانند Timezone ها و Country ها.
    شامل منطق خواندن از دیتابیس (با استفاده از اسکیما) و به‌روزرسانی از API خارجی.
    """

    async def get_timezones_from_db(self, db: AsyncSession) -> List[TimezoneOut]: # <-- تغییر نوع بازگشتی
        """
        Timezone ها را از دیتابیس محلی بازیابی می کند و به صورت Pydantic schema برمی گرداند.

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            لیستی از اشیاء TimezoneOut schema.
        """
        logger.info("Fetching timezones from database...")
        repo = TimezoneRepository(db)
        try:
            # فراخوانی متد ریپازیتوری برای گرفتن همه timezone ها (اشیاء مدل SQLAlchemy)
            timezone_objects = await repo.get_all_timezones()

            # --- تبدیل لیست اشیاء مدل به لیست اشیاء اسکیما ---
            # با فرض اینکه TimezoneOut دارای model_config = ConfigDict(from_attributes=True) است
            timezone_schemas = [TimezoneOut.model_validate(tz) for tz in timezone_objects]
            # --------------------------------------------------

            logger.info(f"Successfully retrieved {len(timezone_schemas)} timezones from DB.")
            return timezone_schemas # <-- برگرداندن لیست اسکیماها
        except Exception as e:
            logger.exception("Failed to retrieve timezones from database.")
            # خطا را دوباره raise کن تا روتر آن را مدیریت کند
            raise Exception("Database error occurred while fetching timezones.") from e

    async def update_timezones_from_api(self, db: AsyncSession) -> int:
        """
        Timezone ها را از API خارجی (API-Football) دریافت کرده و
        کل لیست timezone های موجود در دیتابیس را با آن جایگزین می کند.
        (این متد تغییر زیادی نکرده چون با داده خام API کار می کند و به ریپازیتوری می دهد)

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            تعداد timezone هایی که با موفقیت در دیتابیس ذخیره شدند.

        Raises:
            Exception: اگر خطایی در ارتباط با API خارجی یا نوشتن در دیتابیس رخ دهد.
        """
        logger.info("Starting timezone update process from API...")
        repo = TimezoneRepository(db)
        fetched_count = 0
        try:
            # 1. دریافت لیست timezone ها از API خارجی (هنوز لیست رشته ها است)
            logger.debug("Fetching timezones from external API...")
            timezone_names_from_api = await api_football.fetch_timezones_from_api()

            if timezone_names_from_api is None or not isinstance(timezone_names_from_api, list):
                logger.error("Invalid data received from API client (expected list of strings).")
                raise Exception("Internal Error: Invalid data format received from API client.")

            if not timezone_names_from_api:
                logger.warning("Received empty list of timezones from API. No update performed.")
                return 0

            logger.debug(f"Fetched {len(timezone_names_from_api)} timezones from API.")

            # 2. جایگزینی داده ها در دیتابیس توسط ریپازیتوری
            # ریپازیتوری مسئول تبدیل این رشته ها به مدل Timezone است
            logger.debug("Replacing all timezones in the database...")
            fetched_count = await repo.replace_all_timezones(timezone_names_from_api)
            logger.info(f"Successfully updated timezones in DB. {fetched_count} timezones stored.")
            return fetched_count

        except Exception as e: # گرفتن خطاهای کلاینت API یا دیتابیس
            logger.exception(f"Failed to update timezones from API: {type(e).__name__}")
            raise e


    async def get_countries_from_db(self, db: AsyncSession) -> List[CountryOut]: # <-- تغییر نوع بازگشتی
        """
        کشورها را از دیتابیس محلی بازیابی می کند و به صورت Pydantic schema برمی گرداند.

         Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            لیستی از اشیاء CountryOut schema.
        """
        logger.info("Fetching countries from database...")
        repo = CountryRepository(db)
        try:
            # فراخوانی متد ریپازیتوری برای گرفتن همه کشورها (اشیاء مدل SQLAlchemy)
            countries_objects = await repo.get_all_countries()

            # --- تبدیل لیست اشیاء مدل به لیست اشیاء اسکیما ---
            # با فرض اینکه CountryOut دارای model_config = ConfigDict(from_attributes=True) است
            countries_schemas = [CountryOut.model_validate(c) for c in countries_objects]
            # --------------------------------------------------

            logger.info(f"Successfully retrieved {len(countries_schemas)} countries from DB.")
            return countries_schemas # <-- برگرداندن لیست اسکیماها
        except Exception as e:
            logger.exception("Failed to retrieve countries from database.")
            raise Exception("Database error occurred while fetching countries.") from e

    async def update_countries_from_api(self, db: AsyncSession) -> int:
        """
        کشورها را از API خارجی دریافت کرده و در دیتابیس Upsert می کند.
        (منطق داخلی برای کریمه حفظ شده است)
        (این متد تغییر زیادی نکرده چون با داده خام API کار می کند و به ریپازیتوری می دهد)

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            تعداد تقریبی رکوردهای کشور پردازش شده (نتیجه bulk upsert).

        Raises:
            Exception: اگر خطایی در ارتباط با API خارجی یا نوشتن در دیتابیس رخ دهد.
        """
        logger.info("Starting country update process from API...")
        repo = CountryRepository(db)
        processed_count = 0
        try:
            # 1. Fetch from API (لیست دیکشنری ها)
            logger.debug("Fetching countries from external API...")
            countries_data_from_api = await api_football.fetch_countries_from_api() # فرض می کنیم لیست دیکشنری برمیگرداند

            if not countries_data_from_api or not isinstance(countries_data_from_api, list):
                 logger.warning("Received empty or invalid list of countries from API. No update performed.")
                 return 0

            # --- شروع: اعمال منطق خاص برای کریمه و اعتبارسنجی اولیه ---
            processed_countries_data: List[Dict[str, Any]] = []
            for country_data in countries_data_from_api:
                 if not isinstance(country_data, dict): # اگر داده ورودی دیکشنری نیست، رد کن
                      logger.warning(f"Skipping non-dictionary item in countries data: {country_data}")
                      continue

                 country_name = country_data.get("name")
                 country_code = country_data.get("code")

                 # فقط کشورهایی را پردازش کن که حداقل نام و کد معتبر دارند
                 if not (isinstance(country_name, str) and country_name and isinstance(country_code, str) and country_code):
                      logger.warning(f"Skipping country data with missing/invalid name or code: {country_data}")
                      continue

                 if country_name == "Crimea":
                      logger.info("Applying special case for Crimea: Setting code to UA-CR")
                      country_data["code"] = "UA-CR"
                      # country_data["name"] = "Crimea (UA)" # مثال: تغییر نام (اختیاری)

                 processed_countries_data.append(country_data)
            # ---> پایان: اعمال منطق خاص <---

            if not processed_countries_data:
                 logger.warning("No valid country data remained after processing. No DB update performed.")
                 return 0

            # 2. Upsert data in DB using Repository
            # ریپازیتوری مسئول تبدیل این دیکشنری ها به مدل Country است
            logger.debug(f"Upserting {len(processed_countries_data)} processed countries into the database...")
            # ورودی به ریپازیتوری همچنان لیست دیکشنری ها است
            processed_count = await repo.bulk_upsert_countries(processed_countries_data)
            logger.info(f"Country update process finished. Processed approximately {processed_count} countries.")
            return processed_count

        except Exception as e:
            logger.exception(f"Failed to update countries from API: {type(e).__name__}")
            raise e # خطا را به روتر منتقل کن

# (نمونه سازی و Depends مانند قبل)