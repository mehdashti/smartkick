# app/services/coach_service.py
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
import logging
import math

from app.repositories.coach_repository import CoachRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.league_repository import LeagueRepository

from app.api_clients import api_football
from app.core.config import settings
from app.models import Coach as DBCoach
from app.schemas.coach import (
    CoachCreateInternal,
    CoachApiResponse,
    CoachApiResponseItem,
    CoachBirthData,
)
from app.services.team_service import TeamService


logger = logging.getLogger(__name__)

class CoachService:

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Helper to parse date string, returning None if invalid."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date string: '{date_str}'")
            return None

    def _process_coach_api_data(self, coach_raw_data: CoachApiResponseItem) -> Optional[CoachCreateInternal]:
        
        try:
            if not isinstance(coach_raw_data, CoachApiResponseItem):
                logger.error(f"Invalid input type for coach data: expected CoachApiResponseItem, got {type(coach_raw_data)}")
                return None

            career_data = [career.model_dump() for career in coach_raw_data.career or []]

            for career_item in career_data:
                if not isinstance(career_item, dict) or 'team' not in career_item:
                    logger.error(f"Invalid career item format: {career_item}")
                    return None

            processed_data = CoachCreateInternal(
                id=coach_raw_data.id,
                name=coach_raw_data.name,
                firstname=coach_raw_data.firstname,
                lastname=coach_raw_data.lastname,
                age=coach_raw_data.age,
                birth_date=self._parse_date(coach_raw_data.birth.date) if coach_raw_data.birth else None,
                birth_place=coach_raw_data.birth.place if coach_raw_data.birth else None,
                birth_country=coach_raw_data.birth.country if coach_raw_data.birth else None,
                nationality=coach_raw_data.nationality,
                height=coach_raw_data.height,
                weight=coach_raw_data.weight,
                photo_url=coach_raw_data.photo,
                team_id=coach_raw_data.team.id if coach_raw_data.team else None,
                career=career_data,
            )

            if processed_data.id is None:
                logger.error(f"Processed coach data is missing id! Raw data: {coach_raw_data}")
                return None

            return processed_data

        except Exception as e:
            logger.error(f"Failed to process coach data: {e}", exc_info=True)
            return None


    async def update_coach_by_id(
        self, db: AsyncSession, coach_id: int
    ) -> Optional[DBCoach]:
        logger.info(f"Starting single coach update process for ID: {coach_id}")
        coach_repo = CoachRepository(db)

        try:
            coach_api_data = await api_football.fetch_coach_by_id(coach_id)
            if not coach_api_data:
                logger.warning(f"No coach data found from API for ID: {coach_id}")
                return None
            
            result = CoachApiResponse(**coach_api_data)
            
            if not result.response or len(result.response) == 0:
                logger.warning(f"No coach data found in API response for ID: {coach_id}")
                return None
            
            processed_data = self._process_coach_api_data(result.response[0])
            if not processed_data:
                logger.error(f"Failed to process coach data from API for ID: {coach_id}")
                return None
            coach_data_list = [processed_data.model_dump()]
            upserted_coach = await coach_repo.bulk_upsert_coaches(coach_data_list)
            logger.info(f"Successfully upserted coach (ID: {coach_id})")
            return upserted_coach

        except Exception as e:
            logger.exception(f"Database error during coach upsert for ID {coach_id}: {e}")
            raise