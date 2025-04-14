# app/repositories/country_repository.py
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert # برای Upsert پستگرس

from app.models.country import Country 
import logging

logger = logging.getLogger(__name__)

class CountryRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_all_countries(self) -> List[Country]:
        """تمام کشورهای ذخیره شده را بر اساس نام برمی گرداند."""
        logger.debug("Fetching all countries from DB.")
        stmt = select(Country).order_by(Country.name)
        result = await self.db.execute(stmt)
        countries = result.scalars().all()
        logger.debug(f"Retrieved {len(countries)} countries from DB.")
        return countries

    async def bulk_upsert_countries(self, countries_data: List[Dict[str, Any]]) -> int:
        """
        کشورها را به صورت دسته ای درج یا آپدیت (Upsert) می کند.
        فرض می کند 'code' کلید منحصر به فرد برای تشخیص تداخل است و NULL نیست.

        Args:
            countries_data: لیستی از دیکشنری ها، هر کدام شامل 'name', 'code', 'flag'.

        Returns:
            تعداد رکوردهایی که درج یا آپدیت شدند (تقریبی).
        """
        if not countries_data:
            logger.warning("Received empty list for country upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(countries_data)} countries.")

        # آماده سازی مقادیر برای تابع insert
        values_to_insert = [
            {
                "name": country.get("name"),
                "code": country.get("code"), # فرض می کنیم code همیشه هست
                "flag": country.get("flag")
            }
            for country in countries_data if country.get("code") # فقط آنهایی که code دارند
        ]

        if not values_to_insert:
             logger.warning("No valid country data with non-null 'code' found to upsert.")
             return 0

        # ساخت دستور INSERT ... ON CONFLICT DO UPDATE
        insert_stmt = insert(Country).values(values_to_insert)

        # تعریف ستون هایی که در صورت تداخل آپدیت می شوند
        update_dict = {
            "name": insert_stmt.excluded.name,
            "flag": insert_stmt.excluded.flag,
            # کد را آپدیت نمی کنیم چون کلید تداخل است
        }

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['code'], # ستون یا قید یکتا برای تشخیص تداخل
            set_=update_dict # دیکشنری مقادیر برای آپدیت
        )

        # اجرای دستور Upsert
        async with self.db.begin(): # شروع تراکنش
             result = await self.db.execute(upsert_stmt)

        # result.rowcount ممکن است دقیق نباشد برای ON CONFLICT در برخی درایورها
        # اما نشان دهنده اجرای موفقیت آمیز است
        processed_count = result.rowcount if result.rowcount is not None else len(values_to_insert)
        logger.info(f"Bulk upsert for countries finished. Processed approximately {processed_count} rows.")
        return processed_count # یا len(values_to_insert)