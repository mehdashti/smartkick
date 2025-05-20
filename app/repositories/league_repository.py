# app/repositories/league_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Dict, Any, Optional, Tuple
import logging
from app.models import League as DBLeague

logger = logging.getLogger(__name__)

class LeagueRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_all_leagues(self) -> list[DBLeague]:
        """Fetch all leagues from the database."""
        logger.debug("Fetching all leagues")
        stmt = select(DBLeague)  
        result = await self.db.execute(stmt)
        return result.scalars().all() 

    async def get_current_leagues(self) -> list[DBLeague]:
        """Fetch all current leagues from the database."""
        logger.debug("Fetching all current leagues")
        stmt = select(DBLeague).filter(DBLeague.is_current == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_league_season_pairs(self) -> List[Tuple[int, int]]:
        """
        Retrieves only league_id and season pairs from database
        
        Returns:
            List[Tuple[int, int]]: List of (league_id, season) pairs
        """
        stmt = select(DBLeague.league_id, DBLeague.season).distinct()
        result = await self.db.execute(stmt)
        return result.all()

    

    async def bulk_upsert_leagues(self, leagues_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert leagues."""
        if not leagues_data:
            logger.warning("Received empty list for league upsert.")
            return 0

        valid_leagues_data = [td for td in leagues_data if 'league_id' in td and td['league_id'] is not None]
        if not valid_leagues_data:
            logger.warning("No valid league data with 'league_id' found for bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(valid_leagues_data)} league entries.")
        insert_stmt = pg_insert(DBLeague).values(valid_leagues_data)

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['league_id', 'season'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBLeague.__table__.columns
                if col.name not in ['id', 'league_id', 'season', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(valid_leagues_data)
        except Exception as e:
            logger.exception(f"Database error during league bulk upsert: {e}")
            raise
