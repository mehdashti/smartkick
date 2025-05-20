# app/repositories/team_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Dict, Any, Optional
import logging
from app.models import Team as DBTeam

logger = logging.getLogger(__name__)

class TeamRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_team_by_id(self, team_id: int) -> Optional[DBTeam]:
        """Fetch a team by its ID."""
        logger.debug(f"Fetching team with ID: {team_id}")
        stmt = select(DBTeam).filter(DBTeam.team_id == team_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_teams_by_ids(self, team_ids: List[int]) -> List[DBTeam]:
        """Fetch teams by a list of IDs."""
        if not team_ids:
            return []
        stmt = select(DBTeam).where(DBTeam.team_id.in_(team_ids))
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_all_teams(self) -> list[DBTeam]:
        """Fetch all teams from the database."""
        logger.debug("Fetching all teams")
        stmt = select(DBTeam)  
        result = await self.db.execute(stmt)
        return result.scalars().all() 

    async def get_all_teams_ids(self) -> list[int]:
        """Fetch all team IDs from the database."""
        logger.debug("Fetching all team IDs")
        stmt = select(DBTeam.team_id)  
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def bulk_upsert_teams(self, teams_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert teams."""
        if not teams_data:
            logger.warning("Received empty list for team upsert.")
            return 0

        valid_teams_data = [td for td in teams_data if 'team_id' in td and td['team_id'] is not None]
        if not valid_teams_data:
            logger.warning("No valid team data with 'team_id' found for bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(valid_teams_data)} team entries.")
        insert_stmt = pg_insert(DBTeam).values(valid_teams_data)

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['team_id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBTeam.__table__.columns
                if col.name not in ['name', 'team_id', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(valid_teams_data)
        except Exception as e:
            logger.exception(f"Database error during team bulk upsert: {e}")
            raise
