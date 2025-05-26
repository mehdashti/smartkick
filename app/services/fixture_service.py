# app/services/fixture_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from pydantic import ValidationError
from typing import List, Dict, Any, Optional, Tuple, Set
import logging

from app.core.config import settings
from app.api_clients import api_football
from app.repositories.team_repository import TeamRepository
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.venue_repository import VenueRepository
from app.repositories.league_repository import LeagueRepository
from app.repositories.events_repository import EventsRepository
from app.repositories.lineups_repository import LineupsRepository
from app.repositories.fixture_statistics_repository import FixtureStatisticsRepository
from app.repositories.player_stats_repository import PlayerStatsRepository

from app.services.team_service import TeamService
from app.services.venue_service import VenueService
from app.services.events_service import EventsService
from app.services.lineups_service import LineupsService
from app.services.fixture_statistics_service import FixtureStatisticsService
from app.services.player_stats_service import PlayerStatsService

from app.schemas.match import (
    MatchAPIInputData,
    MatchCreateInternal,
    MatchApiResponse,
)

logger = logging.getLogger(__name__)

class FixtureService:

    async def _process_fixtures_entry(
        self,
        db: AsyncSession,
        raw_entries: List[dict]
    ) -> Tuple[int, int, List[Dict[str, Any]]]:
        fixture_repo = FixtureRepository(db)
        venue_repo = VenueRepository(db)
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
                fixture_data_internal = self._convert_to_internal_schema(
                    validated_data,
                    processed_events_json=entry.get("processed_events"),
                    processed_lineups_json=entry.get("processed_lineups"),
                    processed_team_stats_json=entry.get("processed_team_statistics"),
                    processed_player_stats_json=entry.get("processed_player_statistics")
                )

                if fixture_data_internal.venue_id:
                    if fixture_data_internal.venue_id not in venus_ids_set:
                        logger.info(f"Venue ID {fixture_data_internal.venue_id} not found locally. Attempting to fetch and update from API.")
                        venue_updated_successfully = await venue_service.update_venue_by_id(db, fixture_data_internal.venue_id)

                        if not venue_updated_successfully:
                            logger.warning(
                                f"Dedicated API call for venue ID {fixture_data_internal.venue_id} failed or returned no data. "
                                f"Attempting to use venue data embedded in fixture."
                            )
                             
                            if validated_data.fixture and validated_data.fixture.venue:
                                venue_pydantic_model_from_fixture = validated_data.fixture.venue
                                venue_dict_for_processing = venue_pydantic_model_from_fixture.model_dump(exclude_none=True)
                                processed_data_from_fixture = venue_service._process_venue_data(venue_dict_for_processing)

                                if processed_data_from_fixture:
                                    await venue_repo.bulk_upsert_venues([processed_data_from_fixture])
                                    logger.info(f"Successfully upserted venue ID {fixture_data_internal.venue_id} using data from fixture.")
                                    venus_ids_set.add(fixture_data_internal.venue_id)
                                else:
                                    logger.error(f"Failed to process venue data from fixture for venue ID {fixture_data_internal.venue_id}. Skipping fixture related to this venue or handle as error.")
                            else:
                                logger.warning(f"No venue data embedded in fixture for venue ID {fixture_data_internal.venue_id}. Cannot create/update.")
                        else:
                            venus_ids_set.add(fixture_data_internal.venue_id)

                if fixture_data_internal.home_team_id:
                    if fixture_data_internal.home_team_id not in team_ids_set:
                        logger.info(f"Home Team ID {fixture_data_internal.home_team_id} not found locally. Attempting to fetch and update from API.")
                        await team_service.update_team_by_id(db, fixture_data_internal.home_team_id)
                        team_ids_set.add(fixture_data_internal.home_team_id)
                if fixture_data_internal.away_team_id:
                    if fixture_data_internal.away_team_id not in team_ids_set:
                        logger.info(f"Away Team ID {fixture_data_internal.away_team_id} not found locally. Attempting to fetch and update from API.")
                        await team_service.update_team_by_id(db, fixture_data_internal.away_team_id)
                        team_ids_set.add(fixture_data_internal.away_team_id)

                fixtures_to_upsert.append(fixture_data_internal.model_dump(exclude_unset=True))
                success_count += 1
            except ValidationError as e:
                logger.error(f"Validation error for fixture entry: {entry}, Errors: {e.errors()}") # Log entry for context
                error_count += 1
            except Exception as e:
                logger.error(f"Error processing fixture with entry {entry}: {str(e)}", exc_info=True) # Log entry and full traceback
                error_count += 1

        if fixtures_to_upsert:
            await fixture_repo.bulk_upsert_fixtures(fixtures_to_upsert)

        return success_count, error_count, fixtures_to_upsert

    def _convert_to_internal_schema(
        self,
        api_data: MatchAPIInputData,
        processed_events_json: Optional[List[Dict[str, Any]]] = None,
        processed_lineups_json: Optional[List[Dict[str, Any]]] = None,
        processed_team_stats_json: Optional[List[Dict[str, Any]]] = None,
        processed_player_stats_json: Optional[List[Dict[str, Any]]] = None,
    ) -> MatchCreateInternal:
        """Convert validated API data to internal create schema, prioritizing pre-processed JSON if available."""

        events_json: List[Dict[str, Any]] = []
        if processed_events_json is not None:
            events_json = processed_events_json
        elif api_data.events:
            events_json = [e.model_dump(exclude_none=True) for e in api_data.events]

        lineups_json: List[Dict[str, Any]] = []
        if processed_lineups_json is not None:
            lineups_json = processed_lineups_json
        elif api_data.lineups:
            lineups_json = [l.model_dump(exclude_none=True) for l in api_data.lineups]

        team_stats_json: List[Dict[str, Any]] = []
        if processed_team_stats_json is not None:
            team_stats_json = processed_team_stats_json
        elif api_data.statistics:
            team_stats_json = [s.model_dump(exclude_none=True) for s in api_data.statistics]
        
        player_stats_json_list: List[Dict[str, Any]] = []
        if processed_player_stats_json is not None:
            player_stats_json_list = processed_player_stats_json
        elif api_data.players: # api_data.players is List[PlayerStatisticsParentData]
            for parent_stat_entry in api_data.players:
                # Assuming PlayerStatisticsParentData has a 'players' attribute which is List[PlayerStatisticsData]
                if hasattr(parent_stat_entry, 'players') and parent_stat_entry.players:
                    for player_stat_detail in parent_stat_entry.players:
                        player_stats_json_list.append(player_stat_detail.model_dump(exclude_none=True))
                # If PlayerStatisticsParentData itself is the player stat object (less common for this naming)
                # elif isinstance(parent_stat_entry, PlayerStatisticsData): # Adjust if structure is different
                #    player_stats_json_list.append(parent_stat_entry.model_dump(exclude_none=True))

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
            away_team_id=api_data.teams.away.id,
            winner_home=api_data.teams.home.winner,
            winner_away=api_data.teams.away.winner,
            events_json=events_json,
            lineups_json=lineups_json,
            team_stats_json=team_stats_json,
            player_stats_json=player_stats_json_list
        )

    async def process_comprehensive_fixture_api_response(
        self,
        db: AsyncSession,
        api_response_data: List[dict] 
    ) -> Dict[str, Tuple[int, int]]:
        overall_results = {
            "fixtures": (0, 0),
            "events": (0, 0), # These counts are not updated by this function currently
            "lineups": (0, 0),# but kept for consistency if detailed counts per sub-entity are needed later
            "team_statistics": (0, 0),
            "player_profiles_and_season_stats": (0, 0),
        }

        raw_fixture_entries_from_api = api_response_data # This is List[MatchResponseItem]

        if not raw_fixture_entries_from_api:
            logger.info("No fixture entries found in the API response.")
            return overall_results

        events_service = EventsService()
        lineups_service = LineupsService()
        fixture_statistics_service = FixtureStatisticsService()
        player_stats_service = PlayerStatsService()

        logger.info(f"Processing {len(raw_fixture_entries_from_api)} fixture base entries...")

        base_fixture_data_list = []
        all_events_to_upsert_in_event_table = []
        all_lineups_to_upsert_in_lineup_table = []
        all_team_stats_to_upsert_in_team_stats_table = []
        all_player_stats_to_upsert_in_player_stats_table = []

        for single_fixture_full_data_model in raw_fixture_entries_from_api: 
            current_base_fixture_data = {
                "fixture": single_fixture_full_data_model.fixture, 
                "league": single_fixture_full_data_model.league,
                "teams": single_fixture_full_data_model.teams,
                "goals": single_fixture_full_data_model.goals,
                "score": single_fixture_full_data_model.score,
            }

            match_id = single_fixture_full_data_model.fixture.id
            
            events_list_raw = single_fixture_full_data_model.events 
            if match_id and events_list_raw is not None: 
                try:
                    _, _, current_event_json = await events_service._process_fixture_events_entry(match_id, events_list_raw)
                    current_base_fixture_data["processed_events"] = current_event_json
                    if current_event_json: 
                        all_events_to_upsert_in_event_table.extend(current_event_json)
                except Exception as e:
                    logger.exception(f"Error processing events for match_id {match_id}: {e}")
                    current_base_fixture_data["processed_events"] = [] 
            else:
                current_base_fixture_data["processed_events"] = []



            lineups_list_raw = single_fixture_full_data_model.lineups 
            if match_id and lineups_list_raw:
                try:
                    _, _, current_lineups_json = await lineups_service._process_fixture_lineups_entry(match_id, lineups_list_raw)
                    current_base_fixture_data["processed_lineups"] = current_lineups_json
                    if current_lineups_json:
                        all_lineups_to_upsert_in_lineup_table.extend(current_lineups_json)
                except Exception as e:
                    logger.exception(f"Error processing lineups for match_id {match_id}: {e}")
                    current_base_fixture_data["processed_lineups"] = []
            else:
                current_base_fixture_data["processed_lineups"] = []


            team_statistics_list_raw = single_fixture_full_data_model.statistics 
            if match_id and team_statistics_list_raw is not None:
                try:
                    _, _, match_stats_json = await fixture_statistics_service._process_statistics_entries(match_id, team_statistics_list_raw)
                    current_base_fixture_data["processed_team_statistics"] = match_stats_json 
                    if match_stats_json:
                        all_team_stats_to_upsert_in_team_stats_table.extend(match_stats_json)                   
                except Exception as e:
                    logger.exception(f"Error processing team statistics for match_id {match_id}: {e}")
                    current_base_fixture_data["processed_team_statistics"] = []
            else:
                current_base_fixture_data["processed_team_statistics"] = []


            players_statistics_list_raw = single_fixture_full_data_model.players 
            if match_id and players_statistics_list_raw is not None: 
                try:
                    _, _, match_player_stats_json = await player_stats_service._process_player_fixture_stats_entries(db, match_id, players_statistics_list_raw)
                    current_base_fixture_data["processed_player_statistics"] = match_player_stats_json  
                    if match_player_stats_json:
                        all_player_stats_to_upsert_in_player_stats_table.extend(match_player_stats_json)                  
                except Exception as e:
                    logger.exception(f"Error processing players statistics for match_id {match_id}: {e}")
                    current_base_fixture_data["processed_player_statistics"] = []
            else:
                current_base_fixture_data["processed_player_statistics"] = []

            base_fixture_data_list.append(current_base_fixture_data)
        
        try:
            fixture_success, fixture_errors, _ = await self._process_fixtures_entry(db, base_fixture_data_list)
            overall_results["fixtures"] = (fixture_success, fixture_errors)
            if all_events_to_upsert_in_event_table:
                event_repo = EventsRepository(db) 
                await event_repo.bulk_upsert_events(all_events_to_upsert_in_event_table)
            if all_lineups_to_upsert_in_lineup_table:
                lineups_repo = LineupsRepository(db)
                await lineups_repo.bulk_upsert_lineups(all_lineups_to_upsert_in_lineup_table)
            if all_team_stats_to_upsert_in_team_stats_table:
                team_stats_repo = FixtureStatisticsRepository(db)
                await team_stats_repo.bulk_upsert_statistics(all_team_stats_to_upsert_in_team_stats_table)
            if all_player_stats_to_upsert_in_player_stats_table:
                player_stats_repo = PlayerStatsRepository(db)
                await player_stats_repo.bulk_upsert_player_fixture_stats(all_player_stats_to_upsert_in_player_stats_table)
            overall_results["events"] = (len(all_events_to_upsert_in_event_table), len(raw_fixture_entries_from_api))
            overall_results["lineups"] = (len(all_lineups_to_upsert_in_lineup_table), len(raw_fixture_entries_from_api))
            overall_results["team_statistics"] = (len(all_team_stats_to_upsert_in_team_stats_table), len(raw_fixture_entries_from_api))
            overall_results["player_profiles_and_season_stats"] = (len(all_player_stats_to_upsert_in_player_stats_table), len(raw_fixture_entries_from_api))
        except Exception as e:
            logger.exception(f"Error during bulk processing of fixture base entries: {e}")
            overall_results["fixtures"] = (0, len(raw_fixture_entries_from_api)) 

        logger.info(f"Comprehensive fixture data processing finished. Overall Results: {overall_results}")
        return overall_results

    async def update_fixtures_by_ids(
        self,
        db: AsyncSession,
        match_ids: List[int],
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE 
    ) -> Tuple[int, int]: # Should return Dict[str, Tuple[int, int]] to match process_comprehensive_fixture_api_response
        logger.info(f"Updating fixture details for matches={match_ids}")

        api_result = await api_football.fetch_fixtures_by_ids(match_ids)

        if not api_result or "response" not in api_result or not api_result["response"]:
            logger.error(f"Invalid or empty API response for full fixture data (match_ids: {match_ids}). API Result: {api_result}")
            return (0, len(match_ids) if match_ids else 1) 

        try:
            validated_api_response = MatchApiResponse(**api_result)
            fixtures_data = validated_api_response.response 
            if not fixtures_data: 
                logger.warning(f"No valid fixture data in API response after validation for match_ids: {match_ids}")
                return (0,0) 
        except ValidationError as e:
            logger.error(f"Pydantic validation error for API response (match_ids: {match_ids}): {e.errors()}")
            return (0, len(match_ids) if match_ids else 1) 

        # The return type should be Dict[str, Tuple[int, int]]
        results_dict = await self.process_comprehensive_fixture_api_response(db, fixtures_data)
        return results_dict["fixtures"] 

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

        fixtures_list_raw_dicts = api_response_dict.get("response")

        if not fixtures_list_raw_dicts or not isinstance(fixtures_list_raw_dicts, list):
            logger.warning(f"No fixtures found in API response or 'response' key is not a list. API Response: {api_response_dict}")
            return (0, 0)

        success_count, error_count, _ = await self._process_fixtures_entry(db, fixtures_list_raw_dicts)
        return success_count, error_count