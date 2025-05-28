# app/repositories/coach_repository.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models import Coach as DBCoach
import logging

logger = logging.getLogger(__name__)

class CoachRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_coach_by_id(self, coach_id: int) -> Optional[DBCoach]:
        """Fetch a coach by its ID."""
        logger.debug(f"Fetching coach with ID: {coach_id}")
        stmt = select(DBCoach).filter(DBCoach.id == coach_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_coachs_ids(self) -> List[int]:
        """Fetch all coach IDs."""
        stmt = select(DBCoach.id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def bulk_upsert_coaches(self, coachs_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert coachs with simplified architecture similar to teams"""
        if not coachs_data:
            logger.warning("Received empty list for coach bulk upsert.")
            return 0

        valid_coachs_data = [pd for pd in coachs_data if 'id' in pd and pd['id'] is not None]
        if not valid_coachs_data:
            logger.warning("No valid coach data with 'id' found for bulk upsert.")
            return 0

        logger.info(f"Bulk upserting {len(valid_coachs_data)} coachs")

        insert_stmt = pg_insert(DBCoach).values(valid_coachs_data)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBCoach.__table__.columns
                if col.name not in ['id', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(valid_coachs_data)
        except Exception as e:
            logger.exception(f"Coach bulk upsert failed: {e}")
            raise