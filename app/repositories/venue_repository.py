# app/repositories/venue_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert # برای PostgreSQL
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Dict, Any, Optional
import logging

from app.models import Venue as DBVenue

logger = logging.getLogger(__name__)

class VenueRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_venue_by_external_id(self, external_id: int) -> Optional[DBVenue]:
        """ورزشگاه را بر اساس شناسه خارجی آن پیدا می‌کند."""
        stmt = select(DBVenue).filter(DBVenue.external_id == external_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def upsert_venue(self, venue_data: Dict[str, Any]) -> DBVenue:
        """
        یک ورزشگاه را بر اساس external_id درج یا آپدیت می‌کند.
        Args:
            venue_data: دیکشنری حاوی داده‌های ورزشگاه (باید شامل external_id باشد).
        Returns:
            آبجکت DBVenue درج شده یا آپدیت شده.
        Raises:
            Exception: در صورت بروز خطای دیتابیس.
        """
        if not venue_data or 'external_id' not in venue_data:
             raise ValueError("Venue data must include 'external_id' for upsert.")

        external_id = venue_data['external_id']
        logger.debug(f"Upserting venue with external_id: {external_id}")

        insert_stmt = pg_insert(DBVenue).values(venue_data)

        # ---> شروع تغییر <---
        # تعریف set_ مستقیما در on_conflict_do_update
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['external_id'], # ستون(های) Unique Key
            # دیکشنری set_ در اینجا تعریف می‌شود
            set_={
                # دسترسی به مقادیر excluded در اینجا
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBVenue.__table__.columns
                # ستون‌هایی که نباید آپدیت شوند
                if col.name not in ['venue_id', 'external_id', 'created_at']
            }
        ).returning(DBVenue) # بازگرداندن رکورد آپدیت/درج شده
        # ---> پایان تغییر <---



        try:
            result = await self.db.execute(upsert_stmt)
            # چون از returning استفاده کردیم، باید یک ردیف برگرداند
            upserted_venue = result.scalars().one()
            # Flush برای اطمینان از اعمال تغییرات در session قبل از بازگشت
            # await self.db.flush([upserted_venue]) # شاید لازم نباشد چون commit در get_db است
            logger.debug(f"Venue upsert successful for external_id: {external_id}. Internal ID: {upserted_venue.venue_id}")
            return upserted_venue
        except Exception as e:
            logger.exception(f"Database error during venue upsert for external_id {external_id}: {e}")
            # session.rollback() توسط get_async_db_session مدیریت می‌شود
            raise # خطا را برای مدیریت در لایه بالاتر ارسال کن

    # --- توابع bulk (اگر نیاز باشد در آینده) ---
    async def bulk_upsert_venues(self, venues_data: List[Dict[str, Any]]) -> int:
        """ورزشگاه‌ها را به صورت دسته‌ای Upsert می‌کند."""
        if not venues_data:
            return 0
        logger.info(f"Attempting to bulk upsert {len(venues_data)} venues.")

         # --- استفاده از pg_insert ---
        insert_stmt = pg_insert(DBVenue).values(venues_data)

        # ---> شروع تغییر <---
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['external_id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBVenue.__table__.columns
                if col.name not in ['venue_id', 'external_id', 'created_at']
            }
        )
        # ---> پایان تغییر <---
 
        try:
            result = await self.db.execute(upsert_stmt)
            processed_count = result.rowcount if result.rowcount is not None else len(venues_data)
            logger.info(f"Bulk venue upsert finished. Processed approx: {processed_count} rows.")
            return processed_count
        except Exception as e:
            logger.exception(f"Error during venue bulk upsert: {e}")
            raise