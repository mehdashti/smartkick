# app/repositories/timezone_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import logging

from app.models import Timezone as DBtimezone

logger = logging.getLogger(__name__)

class TimezoneRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_timezone_by_id(self, timezone_id: int) -> Optional[DBtimezone]:
        logger.debug(f"Fetching timezone with ID: {timezone_id}")
        stmt = select(DBtimezone).filter(DBtimezone.timezone_id == timezone_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_timezones_by_ids(self, timezone_ids: List[int]) -> List[DBtimezone]:
        if not timezone_ids:
            return []
        stmt = select(DBtimezone).where(DBtimezone.timezone_id.in_(timezone_ids))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def bulk_upsert_timezones(self, timezone_names: List[str]) -> int:

        if not timezone_names:
            logger.warning("Received empty list for timezone bulk upsert.")
            return 0

        timezones_data = [{"name": name} for name in timezone_names if isinstance(name, str)]
        
        if not timezones_data:
            logger.warning("No valid timezone names provided for bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(timezones_data)} timezones.")

        insert_stmt = pg_insert(DBtimezone).values(timezones_data)

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['name'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBtimezone.__table__.columns
                if col.name not in ['timezone_id', 'name', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            logger.info(f"Timezone bulk upsert completed. Affected rows: {result.rowcount}")
            return result.rowcount if result.rowcount is not None else len(timezones_data)
        except Exception as e:
            logger.exception(f"Error during timezone bulk upsert: {e}")
            raise
