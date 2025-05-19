# app/repositories/country_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.sql import func
import logging

from app.models import Country as DBcountry

logger = logging.getLogger(__name__)

class CountryRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_all_countries(self):
        result = await self.db.execute(select(DBcountry))
        return result.scalars().all()

    async def bulk_upsert_countries(self, countries_data: List[Dict[str, Any]]) -> int:

        if not countries_data:
            logger.warning("Received empty list for country bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(countries_data)} countries.")

        insert_stmt = pg_insert(DBcountry).values(countries_data)

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['name'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBcountry.__table__.columns
                if col.name not in ['country_id', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            logger.info(f"country bulk upsert statement executed for {len(countries_data)} items. Affected rows: {result.rowcount}")
            return result.rowcount if result.rowcount is not None else len(countries_data)
        except Exception as e:
            logger.exception(f"Error during country bulk upsert: {e}")
            raise


    async def get_country_by_name(self, name: str) -> Optional[DBcountry]:
        """
        کشور را بر اساس نام آن پیدا می‌کند (بدون حساسیت به بزرگی و کوچکی حروف).
        """
        logger.debug(f"Querying DB for country with name: {name}")
        # استفاده از ilike برای جستجوی بدون حساسیت به حروف در PostgreSQL
        # یا استفاده از func.lower برای سازگاری بیشتر
        stmt = select(DBcountry).filter(func.lower(DBcountry.name) == func.lower(name))
        result = await self.db.execute(stmt)
        country = result.scalars().first()
        if country:
            logger.debug(f"Country found by name '{name}': ID {country.country_id}")
        else:
            logger.warning(f"Country with name '{name}' not found in DB.")
        return country

