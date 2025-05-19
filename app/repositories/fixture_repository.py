from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models import Match
import logging

logger = logging.getLogger(__name__)

class FixtureRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def bulk_upsert_fixtures(self, fixtures_data: List[Dict[str, Any]]) -> int:
        """
        Bulk upsert with dynamic column handling (similar to your DBPlayer approach)
        """
        insert_stmt = pg_insert(Match).values(fixtures_data)
        
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['match_id'],  # Primary key or unique constraint
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in Match.__table__.columns
                if col.name not in ['match_id', 'created_at']  # Exclude fields
            }
        )
        
        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else 0
        except Exception as e:
            logger.exception(f"Fixture bulk upsert failed: {e}")
            raise        
