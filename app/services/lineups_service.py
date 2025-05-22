# app/services/lineups_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.lineups_repository import LineupsRepository
from app.repositories.team_repository import TeamRepository
from app.services.team_service import TeamService
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

        api_result = await api_football.fetch_lineups_by_id(match_id)

        #if not api_result or not isinstance(api_result, list):
        #    logger.warning(f"No fixture lineups found in API response. API Response: {api_result}")
        #    return (0, 0)
        response_list = api_result.get('response')
        return await self._process_fixture_lineups_entry(db, match_id, response_list)



    async def _process_fixture_lineups_entry(
        self,
        db: AsyncSession,
        match_id_param: int,
        raw_entries: List[dict] 
    ) -> Tuple[int, int]:

        team_repo = TeamRepository(db)
        team_service = TeamService()
        lineup_repo = LineupsRepository(db)

        existing_team_ids = set(await team_repo.get_all_teams_ids()) 

        success_count = 0
        error_count = 0

        lineups_to_upsert_internal_models = []

        for single_team_lineup_dict in raw_entries:
            try:
                # اعتبارسنجی داده‌های ترکیب یک تیم با اسکیمای SingleTeamLineupDataFromAPI
                validated_team_data = SingleTeamLineupDataFromAPI(**single_team_lineup_dict)

                if not validated_team_data.team or not validated_team_data.team.id:
                    logger.warning(f"Skipping lineup entry due to missing team data or team ID in API response for match {match_id_param}")
                    error_count += 1
                    continue

                team_id = validated_team_data.team.id


                if team_id not in existing_team_ids:
                    logger.info(f"Team ID {team_id} for match {match_id_param} not found locally. Attempting to update/create from API...")
                    team_updated_or_created = await team_service.update_team_by_id(db, team_id)
                    if team_updated_or_created:
                        existing_team_ids.add(team_id)
                        logger.info(f"Team ID {team_id} successfully updated/created.")
                    else:
                        logger.warning(f"Failed to update/create team ID {team_id} for match {match_id_param}. Skipping lineup for this team.")
                        error_count += 1
                        continue

                # پردازش startXI
                start_xi_for_db = None
                if validated_team_data.startXI: # validated_team_data.startXI is List[PlayerEntrySchema]
                    processed_players_startxi = [
                        p_entry.player.model_dump(exclude_none=True)
                        for p_entry in validated_team_data.startXI
                        if p_entry.player # PlayerEntrySchema has a 'player' field of type PlayerDetailSchema
                    ]
                    start_xi_for_db = processed_players_startxi if processed_players_startxi else None

                # پردازش substitutes
                substitutes_for_db = None
                if validated_team_data.substitutes: # validated_team_data.substitutes is List[PlayerEntrySchema]
                    processed_players_subs = [
                        s_entry.player.model_dump(exclude_none=True)
                        for s_entry in validated_team_data.substitutes
                        if s_entry.player
                    ]
                    substitutes_for_db = processed_players_subs if processed_players_subs else None

                team_colors_for_db = None
                if validated_team_data.team and validated_team_data.team.colors:
                    team_colors_for_db = validated_team_data.team.colors.model_dump(exclude_none=True)

                lineup_create_data = MatchLineupCreateInternal(
                    match_id=match_id_param,
                    team_id=team_id,
                    team_name=validated_team_data.team.name,
                    formation=validated_team_data.formation,
                    startXI=start_xi_for_db,
                    substitutes=substitutes_for_db,
                    coach_id=validated_team_data.coach.id if validated_team_data.coach else None,
                    coach_name=validated_team_data.coach.name if validated_team_data.coach else None,
                    coach_photo=str(validated_team_data.coach.photo) if validated_team_data.coach and validated_team_data.coach.photo else None,
                    team_colors=team_colors_for_db
                )
                lineups_to_upsert_internal_models.append(lineup_create_data)
                success_count += 1

            except ValidationError as e:
                logger.error(f"Pydantic validation error for single team lineup (match_id: {match_id_param}): {e.errors()} - Input: {single_team_lineup_dict}")
                error_count += 1
            except Exception as e:
                logger.exception(f"Unexpected error processing lineup (match_id: {match_id_param}): {str(e)} - Input: {single_team_lineup_dict}")
                error_count += 1

        if lineups_to_upsert_internal_models:
            # تبدیل مدل‌های داخلی به دیکشنری برای ارسال به ریپازیتوری
            lineup_dicts_for_db = [model.model_dump(exclude_unset=True) for model in lineups_to_upsert_internal_models]
            try:
                await lineup_repo.bulk_upsert_lineups(lineup_dicts_for_db)
                logger.info(f"Successfully attempted to upsert {len(lineup_dicts_for_db)} lineups for match_id {match_id_param}.")
            except Exception as e:
                logger.exception(f"Database error during lineup bulk upsert for match_id {match_id_param}: {e}")
                # تنظیم مجدد شمارنده‌ها اگر آپسرت گروهی خطا داد
                error_count += len(lineup_dicts_for_db)
                success_count -= len(lineup_dicts_for_db) # اگر قبلاً success_count برای اینها اضافه شده بود

        return (success_count, error_count)


