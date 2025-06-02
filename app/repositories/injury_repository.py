# app/repository/injury_repository.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.models import Injury as DBInjury
import logging

logger = logging.getLogger(__name__)

class InjuryRepository:
    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    async def bulk_upsert_injuries(self, injuries_data: List[Dict[str, Any]]) -> int:
        
        insert_stmt = pg_insert(DBInjury).values(injuries_data)
        
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=['player_id', 'match_id'],  
            set_={
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in DBInjury.__table__.columns
                if col.name not in ['id', 'player_id', 'match_id', 'created_at']  
            }
        )
        
        try:
            result = await self.db.execute(upsert_stmt)
            return result.rowcount if result.rowcount is not None else 0
        except Exception as e:
            logger.exception(f"Injury bulk upsert failed: {e}")
            raise        

