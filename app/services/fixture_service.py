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
from app.services.team_service import TeamService
from app.services.venue_service import VenueService
from app.schemas.match import (
    MatchAPIInputData,
    MatchCreateInternal,
)

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





    # --- تابع اصلی برای پردازش پاسخ جامع API ---
    async def process_comprehensive_fixture_api_response(
        self,
        db: AsyncSession,
        api_response_data: Dict[str, Any]
    ) -> Dict[str, Tuple[int, int]]:
        overall_results = {
            "fixtures": (0, 0),
            "events": (0, 0),
            "lineups": (0, 0),
            "team_statistics": (0, 0),
            "player_profiles_and_season_stats": (0, 0), # نام را برای وضوح تغییر دادم
        }

        if "response" not in api_response_data or not isinstance(api_response_data["response"], list):
            logger.error("Invalid API response structure: 'response' key missing or not a list.")
            return overall_results

        raw_fixture_entries_from_api = api_response_data["response"]

        if not raw_fixture_entries_from_api:
            logger.info("No fixture entries found in the API response.")
            return overall_results

        # نمونه‌سازی سرویس‌ها و ریپازیتوری‌های مورد نیاز
        # اینها را می‌توان یک بار در ابتدا ایجاد کرد اگر در حلقه‌ها استفاده می‌شوند
        player_service = PlayerService() # <<< نمونه‌سازی PlayerService
        team_service = TeamService()
        player_repo = PlayerRepository(db)
        player_season_stats_repo = PlayerSeasonStatsRepository(db)
        team_repo = TeamRepository(db) # برای گرفتن ID تیم‌های موجود

        # گرفتن ID تیم‌های موجود برای جلوگیری از فراخوانی‌های غیرضروری API
        # این کار بهتر است یک بار قبل از حلقه‌ها انجام شود.
        existing_team_ids = set(await team_repo.get_all_teams_ids())


        # --------------------------------------------------------------------
        # 1. پردازش اطلاعات اصلی مسابقات (Fixture, League, Teams, Goals, Score)
        # ... (این بخش بدون تغییر باقی می‌ماند) ...
        logger.info(f"Processing {len(raw_fixture_entries_from_api)} fixture base entries...")
        base_fixture_data_list = []
        for single_fixture_full_data in raw_fixture_entries_from_api:
            current_base_fixture_data = {
                "fixture": single_fixture_full_data.get("fixture"),
                "league": single_fixture_full_data.get("league"),
                "teams": single_fixture_full_data.get("teams"),
                "goals": single_fixture_full_data.get("goals"),
                "score": single_fixture_full_data.get("score"),
            }
            # اطمینان از وجود تیم‌ها در دیتابیس (از کد _process_fixtures_entry شما الهام گرفته شده)
            home_team_id = current_base_fixture_data.get("teams", {}).get("home", {}).get("id")
            away_team_id = current_base_fixture_data.get("teams", {}).get("away", {}).get("id")
            if home_team_id and home_team_id not in existing_team_ids:
                logger.info(f"Home team {home_team_id} not found, updating via TeamService...")
                await team_service.update_team_by_id(db, home_team_id)
                existing_team_ids.add(home_team_id)
            if away_team_id and away_team_id not in existing_team_ids:
                logger.info(f"Away team {away_team_id} not found, updating via TeamService...")
                await team_service.update_team_by_id(db, away_team_id)
                existing_team_ids.add(away_team_id)

            base_fixture_data_list.append(current_base_fixture_data)
        try:
            fixture_success, fixture_errors = await self._process_fixtures_entry(db, base_fixture_data_list)
            overall_results["fixtures"] = (fixture_success, fixture_errors)
        except Exception as e:
            logger.exception(f"Error during bulk processing of fixture base entries: {e}")
            overall_results["fixtures"] = (0, len(raw_fixture_entries_from_api))


        # --------------------------------------------------------------------
        # 2. پردازش رویدادها (Events) برای هر مسابقه
        # ... (این بخش بدون تغییر باقی می‌ماند) ...
        all_events_success = 0
        all_events_errors = 0
        for single_fixture_full_data in raw_fixture_entries_from_api:
            match_id = single_fixture_full_data.get("fixture", {}).get("id")
            events_list = single_fixture_full_data.get("events")
            if match_id and events_list is not None:
                mock_events_api_response = {"get": "fixtures/events", "parameters": {"fixture": str(match_id)}, "errors": [], "results": len(events_list), "paging": {"current": 1, "total": 1}, "response": events_list}
                try:
                    s_count, e_count = await self._process_fixture_events_entry(db, match_id, mock_events_api_response)
                    all_events_success += s_count
                    all_events_errors += e_count
                except Exception as e:
                    logger.exception(f"Error processing events for match_id {match_id}: {e}")
                    all_events_errors += len(events_list)
        overall_results["events"] = (all_events_success, all_events_errors)


        # --------------------------------------------------------------------
        # 3. پردازش ترکیب‌ها (Lineups) برای هر مسابقه
        # ... (این بخش بدون تغییر باقی می‌ماند) ...
        all_lineups_success = 0
        all_lineups_errors = 0
        for single_fixture_full_data in raw_fixture_entries_from_api:
            match_id = single_fixture_full_data.get("fixture", {}).get("id")
            lineups_list = single_fixture_full_data.get("lineups")
            if match_id and lineups_list:
                try:
                    s_count, e_count = await self._process_fixture_lineups_entry(db, match_id, lineups_list)
                    all_lineups_success += s_count
                    all_lineups_errors += e_count
                except Exception as e:
                    logger.exception(f"Error processing lineups for match_id {match_id}: {e}")
                    all_lineups_errors += len(lineups_list)
        overall_results["lineups"] = (all_lineups_success, all_lineups_errors)

        # --------------------------------------------------------------------
        # 4. پردازش آمار تیمی (Team Statistics) برای هر مسابقه
        # ... (این بخش بدون تغییر باقی می‌ماند) ...
        all_team_stats_success = 0
        all_team_stats_errors = 0
        for single_fixture_full_data in raw_fixture_entries_from_api:
            match_id = single_fixture_full_data.get("fixture", {}).get("id")
            team_statistics_list = single_fixture_full_data.get("statistics")
            if match_id and team_statistics_list is not None:
                mock_stats_api_response = {"get": "fixtures/statistics", "parameters": {"fixture": str(match_id)},"errors": [],"results": len(team_statistics_list),"paging": {"current": 1, "total": 1},"response": team_statistics_list}
                try:
                    s_count, e_count = await self._process_fixture_statistics_entry(db, match_id, mock_stats_api_response)
                    all_team_stats_success += s_count
                    all_team_stats_errors += e_count
                except Exception as e:
                    logger.exception(f"Error processing team statistics for match_id {match_id}: {e}")
                    all_team_stats_errors += len(team_statistics_list)
        overall_results["team_statistics"] = (all_team_stats_success, all_team_stats_errors)


        # --------------------------------------------------------------------
        # 5. پردازش آمار بازیکنان (Player Profiles & Season Statistics)
        # --------------------------------------------------------------------
        logger.info("Processing player profiles and season statistics...")
        all_player_profiles_upserted_count = 0
        all_player_season_stats_upserted_count = 0
        player_processing_errors = 0

        # جمع‌آوری تمام داده‌های بازیکنان و آمار فصلی آنها از تمام مسابقات
        aggregated_player_data_to_upsert: List[Dict[str, Any]] = []
        aggregated_player_season_stats_to_upsert: List[Dict[str, Any]] = []

        for single_fixture_full_data in raw_fixture_entries_from_api:
            match_id = single_fixture_full_data.get("fixture", {}).get("id")
            # "players" یک لیست است، هر آیتم شامل اطلاعات یک تیم و لیست بازیکنان آن تیم
            teams_with_players_list = single_fixture_full_data.get("players")

            if not (match_id and teams_with_players_list):
                if match_id: logger.info(f"No 'players' data for match_id: {match_id}")
                continue

            for team_entry in teams_with_players_list: # تیم میزبان و میهمان
                # team_info = team_entry.get("team") # اطلاعات تیم (id, name, logo)
                players_in_team_list = team_entry.get("players") # لیست بازیکنان این تیم با آمارشان

                if not players_in_team_list:
                    continue

                for player_api_entry in players_in_team_list:
                    # player_api_entry ساختاری شبیه به ورودی _process_player_and_stats_entry دارد
                    # یعنی {"player": {...}, "statistics": [{...}, ...]}
                    try:
                        # استفاده از متد PlayerService برای پردازش هر بازیکن و آمار فصلی او
                        player_profile_data, player_season_stats_list, teams_in_player_stats = \
                            await player_service._process_player_and_stats_entry(player_api_entry)

                        if player_profile_data and player_profile_data.get("id") is not None:
                            aggregated_player_data_to_upsert.append(player_profile_data)

                        if player_season_stats_list:
                            aggregated_player_season_stats_to_upsert.extend(player_season_stats_list)
                        
                        # اطمینان از وجود تیم‌های ذکر شده در آمار بازیکن در دیتابیس
                        if teams_in_player_stats:
                            for team_id_from_player_stat in teams_in_player_stats:
                                if team_id_from_player_stat and team_id_from_player_stat not in existing_team_ids:
                                    logger.info(f"Team {team_id_from_player_stat} from player stats not found, updating via TeamService...")
                                    await team_service.update_team_by_id(db, team_id_from_player_stat)
                                    existing_team_ids.add(team_id_from_player_stat)

                    except Exception as e:
                        player_id_for_log = player_api_entry.get("player", {}).get("id", "N/A")
                        logger.exception(f"Error processing player entry (ID: {player_id_for_log}) from comprehensive fixture data (match_id: {match_id}): {e}")
                        player_processing_errors += 1
        
        # پس از جمع‌آوری تمام داده‌ها، آپسرت گروهی انجام می‌شود

        # 5.1 آپسرت پروفایل بازیکنان (با حذف موارد تکراری)
        if aggregated_player_data_to_upsert:
            unique_players_map: Dict[int, Dict[str, Any]] = {}
            for p_data in aggregated_player_data_to_upsert:
                p_id = p_data.get("id")
                if p_id is not None:
                    unique_players_map[p_id] = p_data # اگر تکراری باشد، آخرین مورد جایگزین می‌شود
            
            unique_player_list_for_db = list(unique_players_map.values())
            logger.info(f"Attempting to bulk upsert {len(unique_player_list_for_db)} unique player profiles.")
            try:
                count = await player_repo.bulk_upsert_players(unique_player_list_for_db)
                all_player_profiles_upserted_count = count if count is not None else 0
                logger.info(f"Player profiles bulk upsert successful. Count: {all_player_profiles_upserted_count}")
            except Exception as e:
                logger.exception(f"Error during bulk upsert of player profiles: {e}")
                player_processing_errors += len(unique_player_list_for_db)

        # 5.2 آپسرت آمار فصلی بازیکنان (با حذف موارد تکراری بر اساس کلید ترکیبی)
        if aggregated_player_season_stats_to_upsert:
            unique_stats_map: Dict[Tuple[Optional[int], Optional[int], Optional[int], Optional[int]], Dict[str, Any]] = {}
            for s_data in aggregated_player_season_stats_to_upsert:
                # کلید ترکیبی برای تشخیص یکتایی آمار فصلی
                stat_key = (
                    s_data.get("player_id"),
                    s_data.get("team_id"),
                    s_data.get("league_id"),
                    s_data.get("season")
                )
                if all(k is not None for k in stat_key): # اطمینان از وجود تمام بخش‌های کلید
                    unique_stats_map[stat_key] = s_data
            
            unique_season_stats_list_for_db = list(unique_stats_map.values())
            logger.info(f"Attempting to bulk upsert {len(unique_season_stats_list_for_db)} unique player season stats entries.")
            try:
                count = await player_season_stats_repo.bulk_upsert_stats(unique_season_stats_list_for_db)
                all_player_season_stats_upserted_count = count if count is not None else 0
                logger.info(f"Player season stats bulk upsert successful. Count: {all_player_season_stats_upserted_count}")
            except Exception as e:
                logger.exception(f"Error during bulk upsert of player season stats: {e}")
                player_processing_errors += len(unique_season_stats_list_for_db)

        overall_results["player_profiles_and_season_stats"] = (
            all_player_profiles_upserted_count + all_player_season_stats_upserted_count, # شمارش موفقیت کلی
            player_processing_errors
        )
        logger.info(f"Player profiles and season stats processing complete. Upserted Profiles: {all_player_profiles_upserted_count}, Upserted Season Stats: {all_player_season_stats_upserted_count}, Errors: {player_processing_errors}")

        logger.info(f"Comprehensive fixture data processing finished. Overall Results: {overall_results}")
        return overall_results


    async def update_fixtures_by_ids(
        self,
        db: AsyncSession,
        match_ids: List[int],
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating fixture events for match={match_ids}")

        api_result = await api_football.fetch_events_by_id(match_ids)

        return await self.process_comprehensive_fixture_api_response(db, api_result)