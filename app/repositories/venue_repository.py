# app/repositories/venue_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import List, Dict, Any, Optional
import logging
from app.models import Venue as DBVenue

logger = logging.getLogger(__name__)

class VenueRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def get_venue_by_id(self, venue_id: int) -> Optional[DBVenue]:
        """Fetch a venue by its ID."""
        logger.debug(f"Fetching venue with ID: {venue_id}")
        stmt = select(DBVenue).filter(DBVenue.venue_id == venue_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_venues_by_ids(self, venue_ids: List[int]) -> List[DBVenue]:
        """Fetch venues by a list of IDs."""
        if not venue_ids:
            return []
        stmt = select(DBVenue).where(DBVenue.venue_id.in_(venue_ids))
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_all_venues(self) -> list[DBVenue]:
        """Fetch all venues from the database."""
        logger.debug("Fetching all venues")
        stmt = select(DBVenue)  
        result = await self.db.execute(stmt)
        return result.scalars().all() 

    async def bulk_upsert_venues(self, venues_data: List[Dict[str, Any]]) -> int:
        """Bulk upsert venues."""
        if not venues_data:
            logger.warning("Received empty list for venue upsert.")
            return 0

        valid_venues_data = [td for td in venues_data if 'venue_id' in td and td['venue_id'] is not None]
        if not valid_venues_data:
            logger.warning("No valid venue data with 'venue_id' found for bulk upsert.")
            return 0

        logger.info(f"Attempting to bulk upsert {len(valid_venues_data)} venue entries.")
        insert_stmt = pg_insert(DBVenue).values(valid_venues_data)

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['venue_id'],
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBVenue.__table__.columns
                if col.name not in ['name', 'venue_id', 'created_at']
            }
        )

        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else len(valid_venues_data)
        except Exception as e:
            logger.exception(f"Database error during venue bulk upsert: {e}")
            raise
