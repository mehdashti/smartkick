# app/services/injury_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.team_repository import TeamRepository
from app.repositories.injury_repository import InjuryRepository
from app.repositories.venue_repository import VenueRepository
from app.repositories.league_repository import LeagueRepository
from app.repositories.events_repository import EventsRepository
from app.repositories.lineups_repository import LineupsRepository

from app.repositories.player_stats_repository import PlayerStatsRepository

from app.services.team_service import TeamService
from app.services.venue_service import VenueService
from app.services.events_service import EventsService
from app.services.lineups_service import LineupsService

from app.services.player_stats_service import PlayerStatsService

from app.schemas.injury import (
    InjuryApiResponse,
    InjuryApiResponseItem,
    InjuryCreateInternal,
)



logger = logging.getLogger(__name__)

class InjuryService:

    async def _process_injuries_entry(
        self,
        db: AsyncSession,
        raw_entries: InjuryApiResponseItem
    ) -> List[Dict[str, Any]]:
        
        try:
            injury_data_for_db: List[Dict[str, Any]] = []
            for entry in raw_entries:
                injury_data_for_db.append({
                    "player_id": entry.player.id,
                    "team_id": entry.team.id,
                    "match_id": entry.fixture.id,
                    "league_id": entry.league.id,
                    "season": entry.league.season,
                    "type": entry.player.type,
                    "reason": entry.player.reason,         
                })
        except Exception as e:
            logger.error(f"Failed to process injury data: {e}")
            return []
        
        return injury_data_for_db    


    async def update_injuries_by_ids(
        self,
        db: AsyncSession,
        match_ids: List[int],
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE 
    ) -> Tuple[int, int]: # Should return Dict[str, Tuple[int, int]] to match process_comprehensive_injury_api_response
        logger.info(f"Updating injury details for matches={match_ids}")
        injury_repo = InjuryRepository(db)
        
        api_response_dict = await api_football.fetch_injuries_by_ids(match_ids)

        if not api_response_dict:
            logger.warning("Received no response from API for injuries.")
            return None

        result = InjuryApiResponse(**api_response_dict)

        if not result.response or len(result.response) == 0:
            logger.warning(f"No injury data found in API response")
            return None       

        data_for_db = await self._process_injuries_entry(db, result.response)

        if data_for_db:
            upsert_result = await injury_repo.bulk_upsert_injuries(data_for_db)

        return upsert_result

    async def update_injuries_by_league_season(
        self,
        db: AsyncSession,
        league_id: int,
        season: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE 
    ) -> Tuple[int, int]:
        logger.info(f"Updating injuries for league={league_id}, season={season}")
        injury_repo = InjuryRepository(db)

        api_response_dict = await api_football.fetch_injuries_by_league_season(league_id, season)

        if not api_response_dict:
            logger.warning("Received no response from API for injuries.")
            return None

        result = InjuryApiResponse(**api_response_dict)

        if not result.response or len(result.response) == 0:
            logger.warning(f"No injury data found in API response")
            return None       

        data_for_db = await self._process_injuries_entry(db, result.response)

        if data_for_db:
            upsert_result = await injury_repo.bulk_upsert_injuries(data_for_db)

        return upsert_result
