# app/services/player_service.py
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
import logging
import math

from app.repositories.player_repository import PlayerRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.league_repository import LeagueRepository
from app.repositories.player_season_stats_repository import PlayerSeasonStatsRepository
from app.api_clients import api_football
from app.core.config import settings
from app.models import Player as DBPlayer
from app.schemas.player import PlayerAPIInputData 
from app.services.team_service import TeamService


logger = logging.getLogger(__name__)

class PlayerService:
    """
    سرویس برای مدیریت داده‌های بازیکنان.
    """

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Helper to parse date string, returning None if invalid."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date string: '{date_str}'")
            return None

    def _process_player_api_data(self, player_raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        داده خام یک بازیکن از API را به فرمت دیکشنری برای ریپازیتوری تبدیل می‌کند.
        """
        player_id = player_raw_data.get('id')
        if not isinstance(player_id, int):
            logger.error(f"Invalid or missing 'id' (must be int) in raw player data: {player_raw_data}")
            return None

        try:
            validated_raw = PlayerAPIInputData.model_validate(player_raw_data)  # استفاده از کلاس ایمپورت‌شده
            birth_info = validated_raw.birth if validated_raw.birth else {}
            birth_date_parsed = self._parse_date(birth_info.get('date')) if birth_info.get('date') else None

            processed_data = {
                "id": validated_raw.id,
                "name": validated_raw.name,
                "firstname": validated_raw.firstname,
                "lastname": validated_raw.lastname,
                "age": validated_raw.age,
                "birth_date": birth_date_parsed,  # تبدیل رشته تاریخ به datetime.date
                "birth_place": birth_info.get('place'),
                "birth_country": birth_info.get('country'),
                "nationality": validated_raw.nationality,
                "height": validated_raw.height,
                "weight": validated_raw.weight,
                "is_injured": validated_raw.injured,
                "number": validated_raw.number,
                "position": validated_raw.position,
                "photo_url": str(validated_raw.photo) if validated_raw.photo else None,
            }

            if processed_data.get("id") is None:
                logger.error(f"Processed player data is missing id! Raw data: {player_raw_data}")
                return None

            return processed_data

        except Exception as e:
            p_id = player_raw_data.get('id', 'N/A')
            logger.error(f"Failed to process player data for ID={p_id}: {e}", exc_info=True)
            return None

    async def update_player_by_id(
        self, db: AsyncSession, player_id: int
    ) -> Optional[DBPlayer]:
        """
        یک بازیکن را با ID اصلی آن (که از API آمده) از API دریافت و در دیتابیس Upsert می‌کند.
        """
        logger.info(f"Starting single player update process for ID: {player_id}")
        player_repo = PlayerRepository(db)

        try:
            player_api_data = await api_football.fetch_player_profile_by_id(player_id)
            if not player_api_data:
                logger.warning(f"No player profile data found from API for ID: {player_id}")
                return None

            processed_data = self._process_player_api_data(player_api_data)
            if not processed_data:
                logger.error(f"Failed to process player data from API for ID: {player_id}")
                return None

            upserted_player = await player_repo.upsert_player(processed_data)
            logger.info(f"Successfully upserted player (ID: {player_id})")
            return upserted_player

        except Exception as e:
            logger.exception(f"Database error during player upsert for ID {player_id}: {e}")
            raise

    async def update_players_from_api(
        self,
        db: AsyncSession,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> int:
        """
        پروفایل‌های بازیکنان را از API خارجی دریافت کرده و صفحه به صفحه در دیتابیس Upsert می‌کند.
        """
        logger.info("Starting player profiles update process...")
        player_repo = PlayerRepository(db)
        total_entries_submitted = 0
        current_page = 1
        total_pages = 1

        try:
            while True:
                logger.info(f"Fetching API page {current_page} / {total_pages if total_pages > 1 else '?' }...")
                try:
                    api_response = await api_football.fetch_player_profiles_from_api(page=current_page)

                    if not api_response:
                        logger.error(f"Failed to fetch player profiles from API page {current_page}. Stopping update.")
                        break

                    raw_player_list = api_response.get('response', [])
                    paging_info = api_response.get('paging', {})

                    if total_pages == 1:
                        total_pages = paging_info.get('total', 1)
                        logger.info(f"API reports total pages: {total_pages}")

                    if not raw_player_list:
                        logger.info(f"No more player profiles found on page {current_page}.")
                        break

                    logger.debug(f"Processing {len(raw_player_list)} raw player entries from page {current_page}...")
                    page_players_to_upsert = []
                    for player_entry in raw_player_list:
                        player_raw_data = player_entry.get('player')
                        if player_raw_data and isinstance(player_raw_data, dict):
                            processed_player = self._process_player_api_data(player_raw_data)
                            if processed_player:
                                page_players_to_upsert.append(processed_player)
                        else:
                            logger.warning(f"Skipping invalid player entry structure on page {current_page}: {player_entry}")

                    if page_players_to_upsert:
                        logger.debug(f"Upserting {len(page_players_to_upsert)} players from page {current_page}...")
                        try:
                            count_in_page = await player_repo.bulk_upsert_players(page_players_to_upsert)
                            total_entries_submitted += count_in_page
                            logger.debug(f"Page {current_page} upsert finished. Submitted: {count_in_page}")
                        except Exception as batch_error:
                            logger.exception(f"Error upserting players from page {current_page}. Data count: {len(page_players_to_upsert)}. Error: {batch_error}")
                            raise batch_error

                    if current_page >= total_pages:
                        logger.info(f"Fetched last page ({current_page}).")
                        break

                    current_page += 1

                except Exception as e:
                    logger.exception(f"Unexpected error during API fetch or processing page {current_page}: {e}")
                    raise

            logger.info(f"Player update process finished. Total submitted entries: {total_entries_submitted}")
            return total_entries_submitted

        except Exception as e:
            logger.exception(f"Unexpected error during player profiles update: {e}")
            raise

    async def update_player_stats_for_league_season(
            self,
            db: AsyncSession,
            league_id: int,
            season: int,
            batch_size: int = settings.DEFAULT_DB_BATCH_SIZE // 2,
            max_pages: Optional[int] = None,
        ) -> Tuple[int, int]:
            logger.info(f"Starting player stats update for League={league_id}, Season={season} (Batch: {batch_size}, MaxPages: {max_pages or 'All'})")
            stats_repo = PlayerSeasonStatsRepository(db)
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



