# app/services/lineups_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.lineups_repository import LineupsRepository
from app.schemas.match_lineups import (
    MatchLineupApiResponse,
    MatchLineupCreateInternal,
    PlayerEntrySchema,
    SingleTeamLineupDataFromAPI
)


logger = logging.getLogger(__name__)

class LineupsService:


    async def update_fixture_lineups(
        self,
        db: AsyncSession,
        match_id: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixture lineups for match={match_id}")
        lineup_repo = LineupsRepository(db)

        api_result = await api_football.fetch_lineups_by_id(match_id)

        result = MatchLineupApiResponse(**api_result) 
        response_list = result.response


        success_counts, error_counts, lineup_dicts_for_upsert = await self._process_fixture_lineups_entry(match_id, response_list)
        if lineup_dicts_for_upsert:
            try:
                await lineup_repo.bulk_upsert_lineups(lineup_dicts_for_upsert)
                logger.info(f"Successfully attempted to upsert {len(lineup_dicts_for_upsert)} lineups for match_id {match_id}.")
            except Exception as e:
                logger.exception(f"Database error during lineup bulk upsert for match_id {match_id}: {e}")
                error_counts += len(lineup_dicts_for_upsert)
                success_counts -= len(lineup_dicts_for_upsert) 

        return success_counts, error_counts



    async def _process_fixture_lineups_entry(
        self,
        match_id: int,
        raw_entries: List[SingleTeamLineupDataFromAPI] 
    ) -> Tuple[int, int, List[Dict[str, Any]]]:

        success_count = 0
        error_count = 0

        lineups_to_upsert_internal_models = []

        for lineup_data in raw_entries:
            try:

                if not lineup_data.team or not lineup_data.team.id:
                    logger.warning(f"Skipping lineup entry due to missing team data or team ID in API response for match {match_id}")
                    error_count += 1
                    continue

                team_id = lineup_data.team.id

                start_xi_for_db = None
                if lineup_data.startXI: 
                    processed_players_startxi = [
                        p_entry.player.model_dump(exclude_none=True)
                        for p_entry in lineup_data.startXI
                        if p_entry.player 
                    ]
                    start_xi_for_db = processed_players_startxi if processed_players_startxi else None

                substitutes_for_db = None
                if lineup_data.substitutes: 
                    processed_players_subs = [
                        s_entry.player.model_dump(exclude_none=True)
                        for s_entry in lineup_data.substitutes
                        if s_entry.player
                    ]
                    substitutes_for_db = processed_players_subs if processed_players_subs else None

                team_colors_for_db = None
                if lineup_data.team and lineup_data.team.colors:
                    team_colors_for_db = lineup_data.team.colors.model_dump(exclude_none=True)

                lineup_create_data = MatchLineupCreateInternal(
                    match_id=match_id,
                    team_id=team_id,
                    team_name=lineup_data.team.name,
                    formation=lineup_data.formation,
                    startXI=start_xi_for_db,
                    substitutes=substitutes_for_db,
                    coach_id=lineup_data.coach.id if lineup_data.coach else None,
                    coach_name=lineup_data.coach.name if lineup_data.coach else None,
                    coach_photo=str(lineup_data.coach.photo) if lineup_data.coach and lineup_data.coach.photo else None,
                    team_colors=team_colors_for_db
                )
                lineups_to_upsert_internal_models.append(lineup_create_data)
                success_count += 1

            except ValidationError as e:
                logger.error(f"Pydantic validation error for single team lineup (match_id: {match_id}): {e.errors()} - Input: {lineup_data}")
                error_count += 1
            except Exception as e:
                logger.exception(f"Unexpected error processing lineup (match_id: {match_id}): {str(e)} - Input: {lineup_data}")
                error_count += 1

        if lineups_to_upsert_internal_models:
            lineup_dicts_for_db = [model.model_dump(exclude_unset=True) for model in lineups_to_upsert_internal_models]

        return success_count, error_count, lineup_dicts_for_db


