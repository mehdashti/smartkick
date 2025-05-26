# app/services/events_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.events_repository import EventsRepository
from app.schemas.match_event import (
    MatchEventApiResponse,
    SingleEventDataFromAPI,
    MatchEventCreateInternal
)


logger = logging.getLogger(__name__)

class EventsService:


    async def update_fixture_events(
        self,
        db: AsyncSession,
        match_id: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixture events for match={match_id}")
        event_repo = EventsRepository(db)
        
        api_result = await api_football.fetch_events_by_id(match_id)

        result = MatchEventApiResponse(**api_result) 
        response_list = result.response

        success_counts, error_counts, event_dicts_for_upsert = await self._process_fixture_events_entry(match_id, response_list)
        
        if event_dicts_for_upsert:
            try:
                await event_repo.bulk_upsert_events(event_dicts_for_upsert)
                logger.info(f"Successfully attempted to upsert {len(event_dicts_for_upsert)} events for match_id {match_id}.")
            except Exception as e:
                logger.exception(f"Database error during event bulk upsert for match_id {match_id}: {e}")
                error_counts += len(event_dicts_for_upsert) 
                success_counts -= len(event_dicts_for_upsert)

        return success_counts, error_counts


    async def _process_fixture_events_entry(
        self,
        match_id: int,
        event_items_from_api: List[SingleEventDataFromAPI]  
    ) -> Tuple[int, int, List[Dict[str, Any]]]:

        events_to_create_internal = []
        success_count = 0
        error_count = 0

        for event_data in event_items_from_api: 
            try:
                create_data = MatchEventCreateInternal(
                    match_id=match_id,
                    time_elapsed=event_data.time.elapsed,
                    time_extra=event_data.time.extra,
                    team_id=event_data.team.id,
                    team_name_snapshot=event_data.team.name,
                    player_id=event_data.player.id,
                    player_name_snapshot=event_data.player.name,
                    assist_player_id=event_data.assist.id,
                    assist_player_name_snapshot=event_data.assist.name,
                    event_type=event_data.type,
                    event_detail=event_data.detail,
                    comments=event_data.comments
                )
                events_to_create_internal.append(create_data)
                success_count += 1
            except Exception as e: 
                logger.error(f"Error preparing event for DB (match {match_id}): {str(e)} - Input: {event_data}")
                error_count += 1
     
        if events_to_create_internal:
            event_dicts_for_db = [model.model_dump(exclude_unset=True) for model in events_to_create_internal]

        return success_count, error_count, event_dicts_for_db

