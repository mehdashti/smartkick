# app/repositories/team_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Dict, Any, Optional
import logging
from app.core.config import settings 
from app.models import Team as DBTeam

logger = logging.getLogger(__name__)

class TeamRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_team_by_external_id(self, external_id: int) -> Optional[DBTeam]:
        """تیم را بر اساس شناسه خارجی آن پیدا می‌کند."""
        stmt = select(DBTeam).filter(DBTeam.external_id == external_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def bulk_upsert_teams(self, teams_data: List[Dict[str, Any]]) -> int:
        """
        تیم‌ها را به صورت دسته‌ای درج یا آپدیت (Upsert) می‌کند.
        از یک قید UNIQUE بر روی (external_id) استفاده می‌کند.

        Args:
            teams_data: لیستی از دیکشنری‌ها، هر کدام شامل فیلدهای مدل Team
                        (شامل external_id, country_id, venue_id).

        Returns:
            تعداد رکوردهایی که درج یا آپدیت شدند (تقریبی).
        """
        if not teams_data:
            logger.warning("Received empty list for team upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(teams_data)} team entries.")

         # --- استفاده از pg_insert ---
        insert_stmt = pg_insert(DBTeam).values(teams_data)

        # ---> شروع تغییر <---
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['external_id'], # کلید تشخیص تداخل
            set_={
                # دسترسی به مقادیر excluded در اینجا
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBTeam.__table__.columns
                # ستون‌هایی که نباید آپدیت شوند
                if col.name not in ['team_id', 'external_id', 'country_id', 'created_at']
            }
        )
        # ---> پایان تغییر <---


        # اجرای دستور Upsert
        try:
            result = await self.db.execute(upsert_stmt)
            # rowcount ممکن است دقیق نباشد، اما نشان دهنده اجراست
            processed_count = result.rowcount if result.rowcount is not None else len(teams_data)
            logger.info(f"Bulk upsert for teams finished. Processed approximately {processed_count} rows.")
            return processed_count
        except Exception as e:
             # ---> شروع تغییر: لاگ کردن ایمن‌تر <---
            log_message = f"!!! DB Error during team bulk upsert. Type: {type(e).__name__}. Details: {e}"
            # بررسی وجود e.orig و pgcode قبل از دسترسی
            pg_code = getattr(getattr(e, 'orig', None), 'pgcode', None)
            if pg_code:
                log_message += f" | PG Code: {pg_code}"
                # بررسی وجود diag قبل از دسترسی به message_detail
                diag = getattr(e.orig, 'diag', None)
                detail = getattr(diag, 'message_detail', None) if diag else None
                if detail:
                    log_message += f" | Detail: {detail}"

            logger.error(log_message, exc_info=True) # exc_info=True برای traceback کامل
            # ---> پایان تغییر <---
            raise e # خطا را دوباره raise کن
        

    async def update_teams_for_all_countries(
        self,
        db: AsyncSession,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE # می‌توان سایز بچ را کوچک‌تر کرد
    ) -> tuple[int, List[str]]: # برگرداندن تعداد کل و لیست کشورهای ناموفق
        """
        فرآیند به‌روزرسانی تیم‌ها و ورزشگاه‌ها را برای *تمام* کشورهای موجود در دیتابیس اجرا می‌کند.

        Returns:
            یک tuple شامل:
            - تعداد کل تیم‌هایی که در تمام کشورها با موفقیت پردازش شدند.
            - لیستی از نام کشورهایی که در فرآیند به‌روزرسانی آن‌ها خطا رخ داده است.
        """
        logger.info("Starting team/venue update process for ALL countries.")
        country_repo = CountryRepository(db)
        total_processed_count = 0
        failed_countries: List[str] = []

        try:
            # 1. گرفتن لیست همه کشورها از دیتابیس
            # limit=0 یا یک عدد خیلی بزرگ برای گرفتن همه (اگر تعداد کشورها زیاد نیست)
            all_countries = await country_repo.get_all_countries(limit=1000)

            if not all_countries:
                logger.warning("No countries found in the database. Cannot update teams for all countries.")
                return 0, []

            logger.info(f"Found {len(all_countries)} countries in DB. Starting updates for each...")

            # 2. اجرای آپدیت برای هر کشور به صورت جداگانه
            for i, country in enumerate(all_countries):
                country_name = country.name
                logger.info(f"--- Processing country {i+1}/{len(all_countries)}: '{country_name}' ---")
                try:
                    # فراخوانی متد آپدیت برای تک کشور
                    # از همان session دیتابیس استفاده می‌کنیم
                    count_for_country = await self.update_teams_by_country(
                        db=db,
                        country_name=country_name,
                        batch_size=batch_size # از همان batch_size استفاده می‌کنیم
                    )
                    total_processed_count += count_for_country
                    logger.info(f"--- Finished processing for country '{country_name}'. Processed: {count_for_country} teams ---")
                except Exception as country_error:
                    # اگر آپدیت برای یک کشور خطا داد، لاگ کن و به لیست خطاها اضافه کن
                    logger.error(f"!!! Failed to update teams for country '{country_name}'. Error: {type(country_error).__name__} - {country_error}", exc_info=True) # لاگ کامل خطا برای این کشور
                    failed_countries.append(country_name)
                    # ادامه حلقه برای پردازش کشورهای بعدی

            logger.info("Finished team/venue update process for ALL countries.")
            logger.info(f"Total teams processed across all successful countries: {total_processed_count}")
            if failed_countries:
                logger.warning(f"Updates failed for the following countries: {', '.join(failed_countries)}")

            return total_processed_count, failed_countries

        except Exception as e:
            # خطای کلی در گرفتن لیست کشورها یا خطای پیش‌بینی نشده دیگر
            logger.exception("An unexpected error occurred during the 'update all countries' process.")
            # برگرداندن نتیجه فعلی و لیست خطاها (اگر مرحله گرفتن کشورها رد شده باشد)
            return total_processed_count, failed_countries