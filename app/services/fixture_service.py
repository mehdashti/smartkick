# app/services/fixture_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple, Set
import logging



from app.api_clients import api_football
from app.repositories.fixture_repository import FixtureRepository
from app.core.config import settings

from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.match import MatchAPIInputData, MatchCreateInternal
from app.models.match import Match

from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError


logger = logging.getLogger(__name__)

class FixtureService:

    async def _process_fixtures_entry(
        self,
        db: AsyncSession,
        raw_entries: List[dict]
    ) -> Tuple[int, int]:
        """
        Process raw API fixture data using bulk upsert for better performance.
        """
        fixture_repo = FixtureRepository(db)
        
        success_count = 0
        error_count = 0
        fixtures_to_upsert = []

        for entry in raw_entries:
            try:
                # Validate and convert data
                validated_data = MatchAPIInputData(**entry)
                fixture_data = self._convert_to_internal_schema(validated_data)
                fixtures_to_upsert.append(fixture_data.model_dump(exclude_unset=True))
                success_count += 1
            except ValidationError as e:
                logger.error(f"Validation error for fixture entry: {e.errors()}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error processing fixture: {str(e)}")
                error_count += 1

        if fixtures_to_upsert:
            await fixture_repo.bulk_upsert_fixtures(fixtures_to_upsert)

        return (success_count, error_count)


    def _convert_to_internal_schema(self, api_data: MatchAPIInputData) -> MatchCreateInternal:
        """Convert validated API data to internal create schema"""
        return MatchCreateInternal(
            match_id=api_data.fixture.id,
            referee=api_data.fixture.referee,
            timezone=api_data.fixture.timezone,
            date=api_data.fixture.date,
            timestamp=api_data.fixture.timestamp,
            periods_first=api_data.fixture.periods.first,
            periods_second=api_data.fixture.periods.second,
            status_long=api_data.fixture.status.long,
            status_short=api_data.fixture.status.short,
            status_elapsed=api_data.fixture.status.elapsed,
            status_extra=api_data.fixture.status.extra,
            goals_home=api_data.goals.home,
            goals_away=api_data.goals.away,
            score_halftime_home=api_data.score.halftime.home if api_data.score.halftime else None,
            score_halftime_away=api_data.score.halftime.away if api_data.score.halftime else None,
            score_fulltime_home=api_data.score.fulltime.home if api_data.score.fulltime else None,
            score_fulltime_away=api_data.score.fulltime.away if api_data.score.fulltime else None,
            score_extratime_home=api_data.score.extratime.home if api_data.score.extratime else None,
            score_extratime_away=api_data.score.extratime.away if api_data.score.extratime else None,
            score_penalty_home=api_data.score.penalty.home if api_data.score.penalty else None,
            score_penalty_away=api_data.score.penalty.away if api_data.score.penalty else None,
            round=api_data.league.round,
            venue_id=api_data.fixture.venue.id if api_data.fixture.venue else None,
            league_id=api_data.league.id,
            season=api_data.league.season,
            home_team_id=api_data.teams.home.id,
            away_team_id=api_data.teams.away.id
        )


    async def update_fixtures_by_league_season(
        self,
        db: AsyncSession,
        league_id: int,
        season: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixtures for league={league_id}, season={season}")

        # فرض می‌کنیم api_football.fetch_fixtures_by_league_season کل دیکشنری پاسخ را برمی‌گرداند
        api_response_dict = await api_football.fetch_fixtures_by_league_season(league_id, season)

        if not api_response_dict:
            logger.warning("Received no response from API for fixtures.")
            return (0, 0)

        # استخراج لیست بازی‌ها از کلید "response"
        fixtures_list = api_response_dict.get("response")

        if not fixtures_list or not isinstance(fixtures_list, list):
            logger.warning(f"No fixtures found in API response or 'response' key is not a list. API Response: {api_response_dict}")
            return (0, 0)

        # حالا fixtures_list فقط شامل لیست بازی‌ها است
        return await self._process_fixtures_entry(db, fixtures_list)
    






