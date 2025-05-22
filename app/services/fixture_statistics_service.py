# app/services/fixture_statistics_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.fixture_statistics_repository import FixtureStatisticsRepository
from app.schemas.match_team_statistic import (
    MatchTeamStatisticCreateInternal,
    SingleTeamStatisticDataFromAPI, 
    APIStatisticItem,
    MatchStatisticsApiResponse
)

logger = logging.getLogger(__name__)

class FixtureStatisticsService:

    def _transform_api_stats_to_payload(
        self,
        api_statistics_list: List[APIStatisticItem]
    ) -> Dict[str, Any]:
        """
        لیست آمار API (نمونه‌های APIStatisticItem) را به دیکشنری با کلیدهای
        سازگار با اسکیمای MatchTeamStatisticCreateInternal تبدیل می‌کند.
        """
        stat_type_to_field_map = {
            "Shots on Goal": "shots_on_goal",
            "Shots off Goal": "shots_off_goal",
            "Total Shots": "total_shots",
            "Blocked Shots": "blocked_shots",
            "Shots insidebox": "shots_insidebox",
            "Shots outsidebox": "shots_outsidebox",
            "Fouls": "fouls",
            "Corner Kicks": "corner_kicks",
            "Offsides": "offsides",
            "Ball Possession": "ball_possession",
            "Yellow Cards": "yellow_cards",
            "Red Cards": "red_cards",
            "Goalkeeper Saves": "goalkeeper_saves",
            "Total passes": "total_passes",
            "Passes accurate": "passes_accurate",
            "Passes %": "passes_percentage"
        }
        payload = {}
        for stat_item in api_statistics_list: # stat_item is an instance of APIStatisticItem
            field_name = stat_type_to_field_map.get(stat_item.type)
            if field_name:
                payload[field_name] = stat_item.value
        return payload

    async def update_fixture_statistics(
        self,
        db: AsyncSession,
        match_id: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE 
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixture statistics for match_id={match_id}")

        api_response_dict = await api_football.fetch_statistics_by_id(match_id)

        if not api_response_dict or not api_response_dict.get("response"):
            logger.warning(f"No statistics data found in API response for match_id={match_id}. API Response: {api_response_dict}")
            return (0, 0)

        try:
            validated_api_response = MatchStatisticsApiResponse(**api_response_dict)
            raw_statistic_entries = validated_api_response.response
        except ValidationError as e:
            logger.error(f"Pydantic validation error for full statistics API response (match_id: {match_id}): {e.errors()}")
            return (0, 1) 

        return await self._process_statistics_entries(db, match_id, raw_statistic_entries)

    async def _process_statistics_entries(
        self,
        db: AsyncSession,
        match_id_param: int,
        statistic_entries_from_api: List[SingleTeamStatisticDataFromAPI] 
    ) -> Tuple[int, int]:

        statistic_repo = FixtureStatisticsRepository(db)

        statistics_to_upsert_internal = []
        success_count = 0
        error_count = 0

        for team_stat_data in statistic_entries_from_api: # team_stat_data is SingleTeamStatisticDataFromAPI
            try:
                # تبدیل لیست آمار API به دیکشنری برای فیلدهای اختصاصی
                specific_stats_payload = self._transform_api_stats_to_payload(team_stat_data.statistics)

                # آماده‌سازی فیلد raw_statistics
                raw_statistics_for_db = [
                    item.model_dump(exclude_none=True) for item in team_stat_data.statistics
                ]

                statistic_create_data = MatchTeamStatisticCreateInternal(
                    match_id=match_id_param,
                    team_id=team_stat_data.team.id,
                    **specific_stats_payload,
                    raw_statistics=raw_statistics_for_db
                )
                statistics_to_upsert_internal.append(statistic_create_data)
                success_count += 1

            except ValidationError as e: # این خطا نباید اینجا رخ دهد اگر اعتبارسنجی اولیه موفق بوده
                logger.error(f"Pydantic validation error during statistic processing (should not happen if initial validation passed) for match_id {match_id_param}: {e.errors()}")
                error_count += 1
            except Exception as e:
                logger.exception(f"Unexpected error processing statistic for match_id {match_id_param} - Input: {team_stat_data}: {e}")
                error_count += 1

        if statistics_to_upsert_internal:
            statistic_dicts_for_db = [model.model_dump(exclude_unset=True) for model in statistics_to_upsert_internal]
            try:
                await statistic_repo.bulk_upsert_statistics(statistic_dicts_for_db) # متد فرضی
                logger.info(f"Successfully attempted to upsert {len(statistic_dicts_for_db)} team statistics records for match_id {match_id_param}.")
            except Exception as e:
                logger.exception(f"Database error during statistics bulk upsert for match_id {match_id_param}: {e}")
                error_count += len(statistic_dicts_for_db)
                success_count -= len(statistic_dicts_for_db)

        return (success_count, error_count)