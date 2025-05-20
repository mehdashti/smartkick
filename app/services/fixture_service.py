# app/services/fixture_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple, Set
import logging



from app.api_clients import api_football
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.venue_repository import VenueRepository
from app.repositories.league_repository import LeagueRepository
from app.repositories.team_repository import TeamRepository
from app.services.venue_service import VenueService
from app.services.team_service import TeamService
from app.core.config import settings
from app.schemas.match_lineups import MatchLineupAPIData, MatchLineupCreateInternal, PlayerSchema


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
        fixture_repo = FixtureRepository(db)
        venue_repo = VenueRepository(db)
        league_repo = LeagueRepository(db)
        team_repo = TeamRepository(db)
        team_ids_set = set(await team_repo.get_all_teams_ids()) 
        venus_ids_set = set(await venue_repo.get_all_venues_ids()) 
                                                        

        venue_service = VenueService()
        team_service = TeamService()


        success_count = 0
        error_count = 0
        fixtures_to_upsert = []

        for entry in raw_entries:
            try:
                validated_data = MatchAPIInputData(**entry)
                fixture_data = self._convert_to_internal_schema(validated_data)

                if fixture_data.venue_id:
                    if fixture_data.venue_id not in venus_ids_set:
                    
                        logger.info(f"Venue ID {fixture_data.venue_id} not found locally. Attempting to fetch and update from API.")
                        venue_updated_successfully = await venue_service.update_venue_by_id(db, fixture_data.venue_id)

                        if not venue_updated_successfully:
                            
                            logger.warning(
                                f"Dedicated API call for venue ID {fixture_data.venue_id} failed or returned no data. "
                                f"Attempting to use venue data embedded in fixture."
                            )
                            if validated_data.fixture and validated_data.fixture.venue:
                                venue_pydantic_model_from_fixture = validated_data.fixture.venue

                                venue_dict_for_processing = venue_pydantic_model_from_fixture.model_dump(exclude_none=True)

                                processed_data_from_fixture = venue_service._process_venue_data(venue_dict_for_processing)

                                if processed_data_from_fixture:
                                    await venue_repo.bulk_upsert_venues([processed_data_from_fixture])
                                    logger.info(f"Successfully upserted venue ID {fixture_data.venue_id} using data from fixture.")
                                    venus_ids_set.add(fixture_data.venue_id)
                                else:
                                    logger.error(f"Failed to process venue data from fixture for venue ID {fixture_data.venue_id}. Skipping fixture related to this venue or handle as error.")

                            else:
                                logger.warning(f"No venue data embedded in fixture for venue ID {fixture_data.venue_id}. Cannot create/update.")
                        else:
                            venus_ids_set.add(fixture_data.venue_id)

                if fixture_data.home_team_id:
                    if fixture_data.home_team_id not in team_ids_set:
                        logger.info(f"Home Team ID {fixture_data.home_team_id} not found locally. Attempting to fetch and update from API.")
                        await team_service.update_team_by_id(db, fixture_data.home_team_id)
                        team_ids_set.add(fixture_data.home_team_id)
                if fixture_data.away_team_id:
                    if fixture_data.away_team_id not in team_ids_set:
                        logger.info(f"Away Team ID {fixture_data.away_team_id} not found locally. Attempting to fetch and update from API.")
                        await team_service.update_team_by_id(db, fixture_data.away_team_id)
                        team_ids_set.add(fixture_data.away_team_id)

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

        api_response_dict = await api_football.fetch_fixtures_by_league_season(league_id, season)

        if not api_response_dict:
            logger.warning("Received no response from API for fixtures.")
            return (0, 0)

        fixtures_list = api_response_dict.get("response")

        if not fixtures_list or not isinstance(fixtures_list, list):
            logger.warning(f"No fixtures found in API response or 'response' key is not a list. API Response: {api_response_dict}")
            return (0, 0)

        return await self._process_fixtures_entry(db, fixtures_list)





    async def update_fixture_lineups(
        self,
        db: AsyncSession,
        match_id: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixture lineups for match={match_id}")

        api_result = await api_football.fetch_lineups_by_id(match_id)

        if not api_result or not isinstance(api_result, list):
            logger.warning(f"No fixture lineups found in API response. API Response: {api_result}")
            return (0, 0)

        return await self._process_fixture_lineups_entry(db, match_id, api_result)



    async def _process_fixture_lineups_entry(
        self,
        db: AsyncSession,
        match_id_param: int,
        raw_entries: List[dict] 
    ) -> Tuple[int, int]:

        team_repo = TeamRepository(db)
        team_service = TeamService()
        fixture_repo = FixtureRepository(db)  

        existing_team_ids = set(await team_repo.get_all_teams_ids()) 

        success_count = 0
        error_count = 0
        lineups_to_upsert_internal_models = [] # لیستی از مدل‌های Pydantic برای آپسرت

        for entry_dict_from_api_response in raw_entries:
            try:
                # validated_api_data یک نمونه از MatchLineupAPIData خواهد بود
                validated_api_data = MatchLineupAPIData(**entry_dict_from_api_response)

                if not validated_api_data.team or not validated_api_data.team.id:
                    logger.warning(f"Skipping lineup entry due to missing team data or team ID in API response for match {match_id_param}")
                    error_count += 1
                    continue

                team_id = validated_api_data.team.id

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
                if validated_api_data.startXI:
                    processed_players_startxi = []
                    for player_container_dict in validated_api_data.startXI: # player_container_dict is {"player": PlayerSchema(...)}
                        player_schema_instance = player_container_dict.get("player")
                        if isinstance(player_schema_instance, PlayerSchema):
                            processed_players_startxi.append(player_schema_instance.model_dump(exclude_none=True))
                        elif isinstance(player_schema_instance, dict): # اگر به نحوی PlayerSchema ولیدیت نشده بود
                            processed_players_startxi.append(player_schema_instance)
                    start_xi_for_db = processed_players_startxi if processed_players_startxi else None

                # پردازش substitutes
                substitutes_for_db = None
                if validated_api_data.substitutes:
                    processed_players_subs = []
                    for sub_container_dict in validated_api_data.substitutes: # sub_container_dict is {"player": PlayerSchema(...)}
                        sub_schema_instance = sub_container_dict.get("player")
                        if isinstance(sub_schema_instance, PlayerSchema):
                            processed_players_subs.append(sub_schema_instance.model_dump(exclude_none=True))
                        elif isinstance(sub_schema_instance, dict):
                            processed_players_subs.append(sub_schema_instance)
                    substitutes_for_db = processed_players_subs if processed_players_subs else None

                team_colors_for_db = None
                if validated_api_data.team and validated_api_data.team.colors:
                    team_colors_for_db = validated_api_data.team.colors.model_dump(exclude_none=True)

                # ساخت نمونه از MatchLineupCreateInternal
                lineup_create_data = MatchLineupCreateInternal(
                    match_id=match_id_param,
                    team_id=team_id,
                    team_name=validated_api_data.team.name,
                    formation=validated_api_data.formation,
                    startXI=start_xi_for_db,       # این حالا لیستی از دیکشنری‌های بازیکنان است
                    substitutes=substitutes_for_db, # این هم لیستی از دیکشنری‌های بازیکنان است
                    coach_id=validated_api_data.coach.id if validated_api_data.coach else None,
                    coach_name=validated_api_data.coach.name if validated_api_data.coach else None,
                    coach_photo=str(validated_api_data.coach.photo) if validated_api_data.coach and validated_api_data.coach.photo else None,
                    team_colors=team_colors_for_db
                )
                lineups_to_upsert_internal_models.append(lineup_create_data)
                success_count += 1

            except ValidationError as e:
                logger.error(f"Pydantic validation error for lineup (match_id: {match_id_param}): {e.errors()} - Input: {entry_dict_from_api_response}")
                error_count += 1
            except Exception as e:
                # برای دیباگ بهتر، traceback کامل را لاگ کنید
                logger.exception(f"Unexpected error processing lineup (match_id: {match_id_param}): {str(e)} - Input: {entry_dict_from_api_response}")
                error_count += 1

        if lineups_to_upsert_internal_models:
            # تبدیل مدل‌های داخلی به دیکشنری برای ارسال به ریپازیتوری
            lineup_dicts_for_db = [model.model_dump(exclude_none=True, exclude_unset=True) for model in lineups_to_upsert_internal_models]
            try:
                await fixture_repo.bulk_upsert_lineups(lineup_dicts_for_db)
                logger.info(f"Successfully attempted to upsert {len(lineup_dicts_for_db)} lineups for match_id {match_id_param}.")
            except Exception as e:
                logger.exception(f"Database error during lineup bulk upsert for match_id {match_id_param}: {e}")
                # تنظیم مجدد شمارنده‌ها اگر آپسرت گروهی خطا داد
                error_count += len(lineup_dicts_for_db)
                success_count -= len(lineup_dicts_for_db) # اگر قبلاً success_count برای اینها اضافه شده بود

        return (success_count, error_count)


    






