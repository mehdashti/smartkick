# app/repositories/coach_repository.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models import Coach as DBCoach
from app.models import CoachCareers as DBCoachCareers
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


    async def bulk_upsert_coaches(self, coaches_data: List[Dict[str, Any]]) -> int:
        if not coaches_data:
            return 0

        try:
            # استفاده از دستور INSERT ... ON CONFLICT
            stmt = pg_insert(DBCoach).values(coaches_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={
                    c.name: stmt.excluded[c.name]
                    for c in DBCoach.__table__.c
                    if c.name not in ['id', 'created_at']
                }
            )
            
            result = await self.db.execute(stmt)
            return len(coaches_data)
        except Exception as e:
            logger.exception(f"Bulk upsert failed for coaches: {e}")
            raise


    async def bulk_upsert_coaches_careers(self, coachs_careers_data: List[Dict[str, Any]]) -> int:
        if not coachs_careers_data:
            logger.warning("Received empty list for coaches careers bulk upsert.")
            return 0

        insert_stmt = pg_insert(DBCoachCareers).values(coachs_careers_data)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['coach_id', 'team_id', 'start_date'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBCoachCareers.__table__.columns
                if col.name not in ['coach_id', 'team_id', 'start_date', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(coachs_careers_data)
        except Exception as e:
            logger.exception(f"Coach careers bulk upsert failed: {e}")
            raise