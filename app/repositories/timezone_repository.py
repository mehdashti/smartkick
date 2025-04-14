# app/repositories/timezone_repository.py
from typing import List
from sqlalchemy import delete # دستور delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # روش جدیدتر select (اگر از sqlalchemy 1.4+ استفاده می کنید)

from app.models.timezone import Timezone # مدل Timezone

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
        # استفاده از begin برای اطمینان از اتمی بودن عملیات (اختیاری ولی خوب)
        async with self.db.begin():
            # 1. حذف تمام رکوردهای موجود
            delete_stmt = delete(Timezone)
            await self.db.execute(delete_stmt)

            # 2. ایجاد اشیاء مدل Timezone جدید
            # استفاده از set برای حذف موارد تکراری احتمالی از لیست ورودی
            unique_names = set(timezone_names)
            timezone_objects = [Timezone(name=name) for name in unique_names]

            # 3. اضافه کردن اشیاء جدید به session
            self.db.add_all(timezone_objects)

            # نیازی به commit صریح نیست چون از db.begin() استفاده کردیم
            # flush برای اطمینان از ارسال دستورات قبل از پایان (اختیاری)
            await self.db.flush()

        return len(timezone_objects) # تعداد موارد درج شده