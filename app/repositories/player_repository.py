from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models import Player as DBPlayer
import logging

logger = logging.getLogger(__name__)

class PlayerRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_player_by_id(self, player_id: int) -> Optional[DBPlayer]:
        """Fetch a player by its ID."""
        logger.debug(f"Fetching player with ID: {player_id}")
        stmt = select(DBPlayer).filter(DBPlayer.id == player_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_players_by_ids(self, player_ids: List[int]) -> List[DBPlayer]:
        """Fetch players by a list of IDs."""
        if not player_ids:
            return []
        stmt = select(DBPlayer).where(DBPlayer.id.in_(player_ids))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_players_ids(self) -> List[int]:
        """Fetch all player IDs."""
        stmt = select(DBPlayer.id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def upsert_player(self, player_data: Dict[str, Any]) -> None:
        """
        Upsert a single player by ID and return the object.
        """
        if not player_data or 'id' not in player_data:
            raise ValueError("Player data must include 'id' for upsert.")

        player_id = player_data['id']
        logger.debug(f"Upserting player with ID: {player_id}")

        insert_stmt = pg_insert(DBPlayer).values(player_data)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBPlayer.__table__.columns
                if col.name not in ['id', 'created_at']
            }
        )

        try:
            await self.db.execute(upsert_stmt)
            logger.info(f"Upsert completed successfully for player ID: {player_id}")
        except Exception as e:
            logger.exception(f"Database error during player upsert for ID {player_id}: {e}")
            raise

    async def bulk_upsert_players(self, players_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert players with simplified architecture similar to teams"""
        if not players_data:
            logger.warning("Received empty list for player bulk upsert.")
            return 0

        valid_players_data = [pd for pd in players_data if 'id' in pd and pd['id'] is not None]
        if not valid_players_data:
            logger.warning("No valid player data with 'id' found for bulk upsert.")
            return 0

        logger.info(f"Bulk upserting {len(valid_players_data)} players")

        insert_stmt = pg_insert(DBPlayer).values(valid_players_data)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBPlayer.__table__.columns
                if col.name not in ['id', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(valid_players_data)
        except Exception as e:
            logger.exception(f"Player bulk upsert failed: {e}")
            raise