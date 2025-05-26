# app/services/player_service.py
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.ext.asyncio import AsyncSession
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

 