# app/services/player_service.py
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError, BaseModel
from datetime import datetime, date
import logging
import math

from app.repositories.player_repository import PlayerRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.league_repository import LeagueRepository
from app.repositories.player_stats_repository import PlayerStatsRepository
from app.api_clients import api_football
from app.core.config import settings
from app.models import Player as DBPlayer
from app.models import PlayerSeasonStats as DBPlayerSeasonStats
from app.schemas.player import PlayerAPIInputData 
from app.services.team_service import TeamService
from app.services.player_service import PlayerService
from app.schemas.player_fixture_stats import (
    FixturePlayersStatsApiResponse,
    TeamPlayersStatsInFixtureAPI,
    PlayerDetailInFixtureAPI,
    PlayerStatisticsForFixtureAPI,
    PlayerFixtureStatsCreateInternal
)


logger = logging.getLogger(__name__)

class PlayerStatsService:

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Helper to parse date string, returning None if invalid."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date string: '{date_str}'")
            return None


    async def update_player_stats_for_league_season(
            self,
            db: AsyncSession,
            league_id: int,
            season: int,
            batch_size: int = settings.DEFAULT_DB_BATCH_SIZE // 2,
            max_pages: Optional[int] = None,
        ) -> Tuple[int, int]:
            logger.info(f"Starting player stats update for League={league_id}, Season={season} (Batch: {batch_size}, MaxPages: {max_pages or 'All'})")
            stats_repo = PlayerStatsRepository(db)
            player_repo = PlayerRepository(db)
            team_repo = TeamRepository(db)
            team_service = TeamService()


            total_players_processed = 0
            total_stats_processed = 0
            current_page = 1
            total_pages = 1

            teams = await team_repo.get_all_teams()
            existing_team_ids = {team.team_id for team in teams}

            try:
                while True:
                    if max_pages is not None and current_page > max_pages:
                        logger.info(f"Reached max_pages limit ({max_pages}). Stopping fetch for L:{league_id}/S:{season}.")
                        break

                    logger.info(f"Fetching API page {current_page} / {total_pages if total_pages > 1 else '?'} for L:{league_id}/S:{season}...")

                    try:
                        api_response = await api_football.fetch_players_with_stats(
                            league_id=league_id, season=season, page=current_page
                        )

                        if not api_response:
                            logger.error(f"Failed to fetch players/stats page {current_page} for L:{league_id}/S:{season}. Stopping.")
                            break

                        if total_pages == 1:
                            total_pages = api_response.get("paging", {}).get("total", 1)
                            logger.info(f"API reports total pages: {total_pages} for L:{league_id}/S:{season}")

                        response_items = api_response.get('response', [])
                        if not response_items:
                            logger.info(f"No more players found on page {current_page} for L:{league_id}/S:{season}.")
                            break

                        page_stats_data_raw: List[Dict[str, Any]] = []
                        page_player_data_raw: List[Dict[str, Any]] = []                    
                        for entry in response_items:
                            player_data, stats_list, teams_list = await self._process_player_and_stats_entry(entry)
                            if player_data is not None:
                                total_players_processed += 1
                            page_stats_data_raw.extend(stats_list)
                            page_player_data_raw.extend(player_data)

                            new_teams = [team_id for team_id in teams_list if team_id not in existing_team_ids]
                            for team_id in new_teams:
                                await team_service.update_team_by_id(db, team_id)
                                existing_team_ids.add(team_id)
                        

                        unique_stats_map: Dict[Tuple[int, int, int, int], Dict[str, Any]] = {}
                        for stats_item in page_stats_data_raw:
                            key = (
                                stats_item.get('player_id'),
                                stats_item.get('team_id'),
                                stats_item.get('league_id'),
                                stats_item.get('season')
                            )
                            if all(k is not None for k in key):
                                unique_stats_map[key] = stats_item

                        page_stats_data = list(unique_stats_map.values())

                        unique_players_map: Dict[Tuple[int], Dict[str, Any]] = {}
                        for players_item in page_stats_data_raw:
                            key = (
                                players_item.get('player_id'),
                            )
                            if all(k is not None for k in key):
                                unique_players_map[key] = players_item
                        page_player_data = list(unique_players_map.values())
    
                        # Upsert players data
                        if page_player_data:    
                            logger.debug(f"Upserting {len(page_player_data)} unique players entries from page {current_page}...")
                            try:
                                count = await player_repo.bulk_upsert_players(page_player_data)
                                total_players_processed += len(page_player_data)
                                logger.debug(f"Players upsert for page {current_page} finished. Submitted: {len(page_player_data)}")
                            except Exception as player_upsert_error:
                                logger.exception(f"Error during bulk_upsert_players: {player_upsert_error}")
                                raise player_upsert_error
                            
                        # Upsert stats data
                        if page_stats_data:
                            logger.debug(f"Upserting {len(page_stats_data)} unique stats entries from page {current_page}...")
                            try:
                                count = await stats_repo.bulk_upsert_stats(page_stats_data)
                                total_stats_processed += len(page_stats_data)
                                logger.debug(f"Stats upsert for page {current_page} finished. Submitted: {len(page_stats_data)}")
                            except Exception as stats_upsert_error:
                                logger.exception(f"Error during bulk_upsert_stats: {stats_upsert_error}")
                                raise stats_upsert_error

                        if current_page >= total_pages:
                            logger.info(f"Fetched last page ({current_page}) for L:{league_id}/S:{season}.")
                            break

                        current_page += 1

                    except Exception as e:
                        logger.exception(f"Unexpected error processing page {current_page} for L:{league_id}/S:{season}: {e}")
                        raise

            except Exception as e:
                logger.exception(f"Unexpected error during player stats update for League={league_id}, Season={season}: {e}")
                raise

            logger.info(f"Finished player stats update for L:{league_id}/S:{season}. Total Players Updated (approx): {total_players_processed}, Total Stats Upserted: {total_stats_processed}")
            return total_players_processed, total_stats_processed

    async def update_player_stats_for_season(
        self,
        db: AsyncSession,
        season: int,
        **kwargs
    ) -> Tuple[int, int]:
        """
        آمار بازیکنان را برای تمام لیگ‌های یک فصل مشخص آپدیت می‌کند.
        """
        logger.info(f"Starting player stats update for ALL leagues in Season={season}")
        league_repo = LeagueRepository(db)
        leagues = await league_repo.get_leagues_by_season(season)

        if not leagues:
            logger.warning(f"No leagues found in DB for season {season}. Nothing to update.")
            return 0, 0, []

        grand_total_players = 0
        grand_total_stats = 0
        processed_leagues_count = 0
        failed_leagues_info: List[Dict[str, Any]] = []

        for i, league in enumerate(leagues):
            league_id = league.league_id
            league_name = league.name
            logger.info(f"--- Processing League {i+1}/{len(leagues)}: {league_name} (ID: {league_id}), Season: {season} ---")

            try:
                p_count, s_count = await self.update_player_stats_for_league_season(
                    db=db,
                    league_id=league_id,
                    season=season,
                    **kwargs
                )
                grand_total_players += p_count
                grand_total_stats += s_count
                processed_leagues_count += 1
                logger.info(f"--- Successfully processed League: {league_name} (ID: {league_id}), Season: {season}. Players: {p_count}, Stats: {s_count} ---")

            except Exception as e:
                error_msg = f"Failed to update stats for League={league_id}, Season={season}: {type(e).__name__} - {e}"
                logger.error(error_msg, exc_info=True)
                failed_leagues_info.append({
                    "league_id": league_id,
                    "league_name": league_name,
                    "season": season,
                    "error": error_msg
                })
                continue

        logger.info(f"Finished player stats update for Season={season}. Processed {processed_leagues_count}/{len(leagues)} leagues successfully.")
        logger.info(f"Grand Totals - Players Updated (approx): {grand_total_players}, Stats Upserted: {grand_total_stats}")
        if failed_leagues_info:
            logger.warning(f"Updates failed for {len(failed_leagues_info)} leagues. See details above or in the returned list.")

        return grand_total_players, grand_total_stats

    async def update_player_stats_for_league(
        self,
        db: AsyncSession,
        league_id: int,
        **kwargs
    ) -> Tuple[int, int]:
        """
        آمار بازیکنان را برای تمام فصل‌های یک لیگ مشخص آپدیت می‌کند.
        """
        logger.info(f"Starting player stats update for ALL seasons in League Ext ID={league_id}")
        league_repo = LeagueRepository(db)
        seasons = await league_repo.get_seasons_by_league(league_id)

        if not seasons:
            logger.warning(f"No seasons found in DB for league league_id {league_id}. Nothing to update.")
            return 0, 0, []

        grand_total_players = 0
        grand_total_stats = 0
        processed_seasons_count = 0
        failed_seasons_info: List[Dict[str, Any]] = []

        for i, season in enumerate(seasons):
            logger.info(f"--- Processing League: {league_id}, Season: {season} ({i+1}/{len(seasons)}) ---")
            try:
                p_count, s_count = await self.update_player_stats_for_league_season(
                    db=db,
                    league_id=league_id,
                    season=season,
                    **kwargs
                )
                grand_total_players += p_count
                grand_total_stats += s_count
                processed_seasons_count += 1
                logger.info(f"--- Successfully processed League: {league_id}, Season: {season}. Players: {p_count}, Stats: {s_count} ---")

            except Exception as e:
                error_msg = f"Failed to update stats for League={league_id}, Season={season}: {type(e).__name__} - {e}"
                logger.error(error_msg, exc_info=True)
                failed_seasons_info.append({
                    "league_id": league_id,
                    "season": season,
                    "error": error_msg
                })
                continue

        logger.info(f"Finished player stats update for League Ext ID={league_id}. Processed {processed_seasons_count}/{len(seasons)} seasons successfully.")
        logger.info(f"Grand Totals - Players Updated (approx): {grand_total_players}, Stats Upserted: {grand_total_stats}")
        if failed_seasons_info:
            logger.warning(f"Updates failed for {len(failed_seasons_info)} seasons. See details above or in the returned list.")

        return grand_total_players, grand_total_stats

    async def _process_player_and_stats_entry(
        self,
        entry: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[int]]:
        """
        پردازش داده‌های خام بازیکن و آمار آن‌ها.
        """

        try:
            player_raw_data = entry.get("player")
            stats_raw_data = entry.get("statistics", [])

            if not player_raw_data or not isinstance(stats_raw_data, list):
                logger.warning(f"Skipping invalid player entry: {entry}")
                return None, []

            # پردازش داده‌های بازیکن
            birth_date_str = player_raw_data.get("birth", {}).get("date")
            birth_date = self._parse_date(birth_date_str) if birth_date_str else None

            player_data = {
                "id": player_raw_data.get("id"),
                "name": player_raw_data.get("name"),
                "firstname": player_raw_data.get("firstname"),
                "lastname": player_raw_data.get("lastname"),
                "age": player_raw_data.get("age"),
                "birth_date": birth_date,  # تبدیل رشته تاریخ به datetime.date
                "birth_place": player_raw_data.get("birth", {}).get("place"),
                "birth_country": player_raw_data.get("birth", {}).get("country"),
                "nationality": player_raw_data.get("nationality"),
                "height": player_raw_data.get("height"),
                "weight": player_raw_data.get("weight"),
                "photo_url": player_raw_data.get("photo"),
            }
            teams = []
            
            stats_list = []
            for stats_entry in stats_raw_data:
                team_id = stats_entry.get("team", {}).get("id")
                league_id = stats_entry.get("league", {}).get("id")

                teams += [team_id] 

                stats_data = {
                    "player_id": player_data["id"],
                    "team_id": team_id,
                    "league_id": league_id,
                    "season": stats_entry.get("league", {}).get("season"),  
                    "cards_red": stats_entry.get("cards", {}).get("red"),  
                    "cards_yellow": stats_entry.get("cards", {}).get("yellow"),
                    "cards_yellowred": stats_entry.get("cards", {}).get("yellowred"), 
                    "goals_total": stats_entry.get("goals", {}).get("total"), 
                    "goals_assists": stats_entry.get("goals", {}).get("assists"),  
                    "goals_conceded": stats_entry.get("goals", {}).get("conceded"), 
                    "goals_saves": stats_entry.get("goals", {}).get("saves"),  
                    "shots_total": stats_entry.get("shots", {}).get("total"), 
                    "shots_on": stats_entry.get("shots", {}).get("on"),  
                    "passes_total": stats_entry.get("passes", {}).get("total"),  
                    "passes_key": stats_entry.get("passes", {}).get("key"),  
                    "passes_accuracy": stats_entry.get("passes", {}).get("accuracy"),  
                    "tackles_total": stats_entry.get("tackles", {}).get("total"),
                    "tackles_blocks": stats_entry.get("tackles", {}).get("blocks"),
                    "tackles_interceptions": stats_entry.get("tackles", {}).get("interceptions"),
                    "duels_total": stats_entry.get("duels", {}).get("total"),
                    "duels_won": stats_entry.get("duels", {}).get("won"),
                    "dribbles_attempts": stats_entry.get("dribbles", {}).get("attempts"),
                    "dribbles_success": stats_entry.get("dribbles", {}).get("success"),
                    "dribbles_past": stats_entry.get("dribbles", {}).get("past"),
                    "fouls_drawn": stats_entry.get("fouls", {}).get("drawn"),
                    "fouls_committed": stats_entry.get("fouls", {}).get("committed"),
                    "penalty_won": stats_entry.get("penalty", {}).get("won"),
                    "penalty_committed": stats_entry.get("penalty", {}).get("commited"),
                    "penalty_scored": stats_entry.get("penalty", {}).get("scored"),
                    "penalty_missed": stats_entry.get("penalty", {}).get("missed"),
                    "penalty_saved": stats_entry.get("penalty", {}).get("saved"),
                    "sub_in": stats_entry.get("substitutes", {}).get("in"),
                    "sub_out": stats_entry.get("substitutes", {}).get("out"),
                    "sub_bench": stats_entry.get("substitutes", {}).get("bench"),                    
                    "minutes": stats_entry.get("games", {}).get("minutes"),
                    "appearences": stats_entry.get("games", {}).get("appearances"),
                    "lineups": stats_entry.get("games", {}).get("lineups"),
                    "rating": float(stats_entry.get("games", {}).get("rating")) if stats_entry.get("games", {}).get("rating") is not None else None,
                    "captain": stats_entry.get("games", {}).get("captain"),
                    "position": stats_entry.get("games", {}).get("position"),
                    "player_number": stats_entry.get("games", {}).get("number"),  
                }
                stats_list.append(stats_data)

            return player_data, stats_list, teams

        except Exception as e:
            logger.exception(f"Error processing player and stats entry: {e}")
            return None, []



    def _transform_api_fixture_stats_to_internal(
        self,
        api_stats: PlayerStatisticsForFixtureAPI, 
        player_id: int,
        match_id: int,
        team_id: int
    ) -> PlayerFixtureStatsCreateInternal:
        """
        نمونه PlayerStatisticsForFixtureAPI را به PlayerFixtureStatsCreateInternal تبدیل می‌کند.
        """
        return PlayerFixtureStatsCreateInternal(
            player_id=player_id,
            match_id=match_id,
            team_id=team_id,
            minutes_played=api_stats.games.minutes,
            player_number=api_stats.games.number,
            position=api_stats.games.position,
            rating=float(api_stats.games.rating) if api_stats.games.rating is not None else None,
            captain=api_stats.games.captain,
            substitute=api_stats.games.substitute,
            offsides=api_stats.offsides,
            shots_total=api_stats.shots.total,
            shots_on=api_stats.shots.on,
            goals_total=api_stats.goals.total,
            goals_conceded=api_stats.goals.conceded,
            goals_assists=api_stats.goals.assists,
            goals_saves=api_stats.goals.saves,
            passes_total=api_stats.passes.total,
            passes_key=api_stats.passes.key,
            passes_accuracy_percentage=int(str(api_stats.passes.accuracy).replace('%','')) if api_stats.passes.accuracy is not None else None,
            tackles_total=api_stats.tackles.total,
            tackles_blocks=api_stats.tackles.blocks,
            tackles_interceptions=api_stats.tackles.interceptions,
            duels_total=api_stats.duels.total,
            duels_won=api_stats.duels.won,
            dribbles_attempts=api_stats.dribbles.attempts,
            dribbles_success=api_stats.dribbles.success,
            dribbles_past=api_stats.dribbles.past,
            fouls_drawn=api_stats.fouls.drawn,
            fouls_committed=api_stats.fouls.committed,
            cards_yellow=api_stats.cards.yellow,
            cards_red=api_stats.cards.red,
            penalty_won=api_stats.penalty.won,
            penalty_committed=api_stats.penalty.commited, # املای commited بر اساس JSON
            penalty_scored=api_stats.penalty.scored,
            penalty_missed=api_stats.penalty.missed,
            penalty_saved=api_stats.penalty.saved
        )

    async def update_fixture_player_stats_by_id(
        self,
        db: AsyncSession,
        match_id: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        logger.info(f"Updating player statistics for match_id={match_id}")
        player_fixture_stats_repo = PlayerStatsRepository(db)

        api_response_dict = await api_football.fetch_fixture_player_stats(match_id)

        if not api_response_dict or not api_response_dict.get("response"):
            logger.warning(f"No player statistics data found in API response for match_id={match_id}. API Response: {api_response_dict}")
            return (0, 0)

        try:
            validated_api_response = FixturePlayersStatsApiResponse(**api_response_dict)
            teams_with_player_stats = validated_api_response.response
        except ValidationError as e:
            logger.error(f"Pydantic validation error for full player_fixture_stats API response (match_id: {match_id}): {e.errors()}")
            return (0, 1)

        success_counts, error_counts, stat_dicts_for_upsert = await self._process_player_fixture_stats_entries(db, match_id, teams_with_player_stats)
        if stat_dicts_for_upsert:
            try:
                await player_fixture_stats_repo.bulk_upsert_player_fixture_stats(stat_dicts_for_upsert)
                logger.info(f"Successfully attempted to upsert {len(stat_dicts_for_upsert)} player_fixture_stats records for match_id {match_id}.")
            except Exception as e:
                logger.exception(f"Database error during player_fixture_stats bulk upsert for match_id {match_id}: {e}")
                error_count += len(stat_dicts_for_upsert) 
                success_count -= len(stat_dicts_for_upsert) 
        return success_counts, error_counts

    async def _process_player_fixture_stats_entries(
        self,
        db: AsyncSession,
        match_id_param: int,
        teams_data_from_api: List[TeamPlayersStatsInFixtureAPI] 
    ) -> Tuple[int, int, List[Dict[str, Any]]]:

        player_repo = PlayerRepository(db)

        player_service = PlayerService()

        existing_player_ids = set(await player_repo.get_all_players_ids())

        stats_to_upsert_internal = []
        success_count = 0
        error_count = 0

        for team_entry in teams_data_from_api:
            if not team_entry.team or not team_entry.team.id:
                logger.warning(f"Skipping team entry due to missing team data or team ID for match_id {match_id_param}")
                error_count += 1
                continue
            api_team_id = team_entry.team.id
            for player_detail_entry in team_entry.players: 
                try:

                    if not player_detail_entry.player or not player_detail_entry.player.id:
                        logger.warning(f"Skipping player entry due to missing player data or player ID for team {api_team_id}, fixture {match_id_param}")
                        error_count +=1
                        continue

                    api_player_id = player_detail_entry.player.id

                    if api_player_id not in existing_player_ids:
                        logger.info(f"Player ID {api_player_id} (team {api_team_id}, fixture {match_id_param}) not found. Attempting to create/update.")
                        
                        player_created = await player_service.update_player_by_id(db, api_player_id)
                        if player_created:
                            existing_player_ids.add(api_player_id)
                        else:
                            logger.warning(f"Failed to create/update player ID {api_player_id}. Skipping their stats for this fixture.")
                            error_count +=1
                            continue
                    
                    if not player_detail_entry.statistics:
                        logger.info(f"No statistics found for player {api_player_id} in fixture {match_id_param}")
                        continue

                    for single_player_stat_api in player_detail_entry.statistics: 
                        internal_stat_data = self._transform_api_fixture_stats_to_internal(
                            api_stats=single_player_stat_api,
                            player_id=api_player_id,
                            match_id=match_id_param,
                            team_id=api_team_id
                        )
                        stats_to_upsert_internal.append(internal_stat_data)
                        success_count += 1

                except ValidationError as e:
                    logger.error(f"Pydantic validation error during player_fixture_stats processing for fixture {match_id_param}, player {player_detail_entry.player.id if player_detail_entry.player else 'Unknown'}: {e.errors()} - Input: {player_detail_entry.model_dump_json(indent=2)}")
                    error_count += 1
                except Exception as e:
                    logger.exception(f"Unexpected error processing player_fixture_stats for fixture {match_id_param}, player {player_detail_entry.player.id if player_detail_entry.player else 'Unknown'}: {str(e)} - Input: {player_detail_entry.model_dump_json(indent=2) if isinstance(player_detail_entry, BaseModel) else player_detail_entry}")
                    error_count += 1
        
        if stats_to_upsert_internal:
            stat_dicts_for_db = [model.model_dump(exclude_unset=True) for model in stats_to_upsert_internal]


        return success_count, error_count, stat_dicts_for_db