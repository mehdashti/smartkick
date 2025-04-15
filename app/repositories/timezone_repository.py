# app/repositories/timezone_repository.py
from typing import List
from sqlalchemy import delete # دستور delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # روش جدیدتر select (اگر از sqlalchemy 1.4+ استفاده می کنید)

from app.models import Country, Timezone, League
import logging

logger = logging.getLogger(__name__)

class TimezoneRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_all_timezones(self) -> List[Timezone]:
        """تمام timezone های ذخیره شده را برمی گرداند."""
        result = await self.db.execute(select(Timezone).order_by(Timezone.name))
        return result.scalars().all()

    async def replace_all_timezones(self, timezone_names: List[str]) -> int:
        """
        تمام timezone های موجود را حذف کرده و موارد جدید را درج می کند.
        تعداد timezone های درج شده را برمی گرداند.
        """
        # --- حذف `async with self.db.begin()` ---
        try:
            # 1. حذف تمام رکوردهای موجود
            delete_stmt = delete(Timezone)
            await self.db.execute(delete_stmt)
            logger.debug("Executed delete statement for existing timezones.")

            # 2. ایجاد اشیاء مدل Timezone جدید
            unique_names = set(timezone_names)
            timezone_objects = [Timezone(name=name) for name in unique_names]
            logger.debug(f"Prepared {len(timezone_objects)} unique timezone objects for insertion.")


            # 3. اضافه کردن اشیاء جدید به session
            self.db.add_all(timezone_objects)
            logger.debug("Added new timezone objects to the session.")

            # flush اختیاری است، اگر نیاز فوری به ID های جدید ندارید
            # await self.db.flush()
            # logger.debug("Flushed session changes.")

            # Commit نهایی توسط وابستگی انجام می شود
            prepared_count = len(timezone_objects)
            logger.info(f"Successfully prepared {prepared_count} timezones for replacement.")
            return prepared_count # تعداد آماده شده برای درج

        except Exception as e:
            # فقط لاگ و انتشار خطا، Rollback توسط وابستگی انجام می شود
            logger.exception(f"Error during replace all timezones execution: {e}")
            raise e
        # --- پایان حذف ---