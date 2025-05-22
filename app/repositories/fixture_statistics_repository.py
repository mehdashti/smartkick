# app/repository/fixture_statistics_repository.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select, func

from app.models import MatchTeamStatistic
import logging

logger = logging.getLogger(__name__)

class FixtureStatisticsRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def bulk_upsert_statistics(self, statistics_data: List[Dict[str, Any]]) -> int:
        insert_stmt = pg_insert(MatchTeamStatistic).values(statistics_data)
        
        update_values = {
            col.name: getattr(insert_stmt.excluded, col.name)
            for col in MatchTeamStatistic.__table__.columns
            if col.name not in ['id', 'match_id', 'team_id', 'created_at']
        }

        if 'updated_at' in (c.name for c in MatchTeamStatistic.__table__.columns):
            update_values['updated_at'] = func.now()

        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint='uq_match_team_statistic',
            set_=update_values
        )
        
        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else 0
        except Exception as e:
            logger.exception(f"Fixture bulk upsert failed: {e}")
            raise
