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

        api_result = await api_football.fetch_events_by_id(match_id)

        response_list = api_result.get('response')

        return await self._process_fixture_events_entry(db, match_id, response_list)


    async def _process_fixture_events_entry(
        self,
        db: AsyncSession,
        match_id: int,
        event_items_from_api: List[dict]  
    ) -> Tuple[int, int]:
        event_repo = EventsRepository(db)

        events_to_create_internal = []
        success_count = 0
        error_count = 0

        for event_data in event_items_from_api: 
            try:
                validated_event_data = SingleEventDataFromAPI(**event_data)
                create_data = MatchEventCreateInternal(
                    match_id=match_id,
                    time_elapsed=validated_event_data.time.elapsed,
                    time_extra=validated_event_data.time.extra,
                    team_id=validated_event_data.team.id,
                    team_name_snapshot=validated_event_data.team.name,
                    player_id=validated_event_data.player.id,
                    player_name_snapshot=validated_event_data.player.name,
                    assist_player_id=validated_event_data.assist.id,
                    assist_player_name_snapshot=validated_event_data.assist.name,
                    event_type=validated_event_data.type,
                    event_detail=validated_event_data.detail,
                    comments=validated_event_data.comments
                )
                events_to_create_internal.append(create_data)
                success_count += 1
            except Exception as e: 
                logger.error(f"Error preparing event for DB (match {match_id}): {str(e)} - Input: {event_data}")
                error_count += 1
     
        if events_to_create_internal:
            event_dicts_for_db = [model.model_dump(exclude_unset=True) for model in events_to_create_internal]
            try:
                await event_repo.bulk_upsert_events(event_dicts_for_db)
                logger.info(f"Successfully attempted to upsert {len(event_dicts_for_db)} events for match_id {match_id}.")
            except Exception as e:
                logger.exception(f"Database error during event bulk upsert for match_id {match_id}: {e}")
                error_count += len(event_dicts_for_db) 
                success_count -= len(event_dicts_for_db)

        return success_count, error_count



