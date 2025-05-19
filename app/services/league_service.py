# app/services/league_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Tuple, Optional
import logging
import math
from datetime import datetime
from app.api_clients import api_football
from app.repositories.league_repository import LeagueRepository
from app.repositories.country_repository import CountryRepository
from app.core.config import settings


logger = logging.getLogger(__name__)

class LeagueService:
    """
    سرویس برای مدیریت داده‌های لیگ‌ها.
    """

    async def update_league(
        self,
        db: AsyncSession,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> int:
        """
        لیگ‌ها و فصل‌های آن‌ها را از API خارجی دریافت کرده و در دیتابیس Upsert می‌کند.
        """
        logger.info(f"Starting leagues update process... (batch size: {batch_size})")
        league_repo = LeagueRepository(db)
        country_repo = CountryRepository(db)
        total_entries_submitted = 0
        leagues_to_upsert: List[Dict[str, Any]] = []

        try:
            logger.debug("Fetching leagues from external API...")
            raw_league_entries = await api_football.fetch_leagues_from_api()

            if not raw_league_entries:
                logger.warning("Received empty list of league entries from API. No update performed.")
                return 0

            logger.debug(f"Fetched {len(raw_league_entries)} raw league entries from API. Processing...")

            for entry in raw_league_entries:
                league_info = entry.get('league', {})
                country_info = entry.get('country', {})
                seasons_info = entry.get('seasons', [])

                if not league_info or not country_info or not seasons_info or not league_info.get('id'):
                    logger.warning(f"Skipping invalid league entry: missing league, country, seasons or league id. Entry: {entry}")
                    continue

                league_id = league_info.get('id')
                league_name = league_info.get('name')
                league_type = league_info.get('type')
                league_logo = league_info.get('logo')

                country_name = country_info.get('name')
                country = await country_repo.get_country_by_name(country_name)

                if not country:
                    countries_data = [
                        {"name": country_name, "code": country_info.get('code'), "flag_url": country_info.get('flag')}
                      ]
                    await country_repo.bulk_upsert_countries(countries_data)                   
                    country = await country_repo.get_country_by_name(country_name)
                    continue

                for season_data in seasons_info:
                    season_year = season_data.get('year')
                    start_date_str = season_data.get('start')
                    end_date_str = season_data.get('end')
                    is_current = season_data.get('current', False)
                    coverage = season_data.get('coverage', {})
                    fixtures_coverage = coverage.get('fixtures', {})

                    if not all([season_year, start_date_str, end_date_str]):
                        logger.warning(f"Skipping season for league '{league_name}' (ID: {league_id}): Missing year, start_date, or end_date. Data: {season_data}")
                        continue

                    try:
                        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"Skipping season {season_year} for league '{league_name}' (ID: {league_id}): Invalid date format. Start: '{start_date_str}', End: '{end_date_str}'")
                        continue

                    league_season_dict = {
                        "league_id": league_id,
                        "season": season_year,
                        "name": league_name,
                        "country_id": country.country_id,
                        "type": league_type,
                        "start_date": start_date,
                        "end_date": end_date,
                        "is_current": is_current,
                        "logo_url": league_logo,
                        "has_standings": coverage.get('standings', False),
                        "has_players": coverage.get('players', False),
                        "has_top_scorers": coverage.get('top_scorers', False),
                        "has_top_assists": coverage.get('top_assists', False),
                        "has_top_cards": coverage.get('top_cards', False),
                        "has_injuries": coverage.get('injuries', False),
                        "has_predictions": coverage.get('predictions', False),
                        "has_odds": coverage.get('odds', False),
                        "has_events": fixtures_coverage.get('events', False),
                        "has_lineups": fixtures_coverage.get('lineups', False),
                        "has_fixture_stats": fixtures_coverage.get('statistics_fixtures', False),
                        "has_player_stats": fixtures_coverage.get('statistics_players', False),
                    }
                    leagues_to_upsert.append(league_season_dict)

            unique_leagues_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
            for league_data in leagues_to_upsert:
                key = (league_data.get("league_id"), league_data.get("season"))
                if key[0] is not None and key[1] is not None:
                    unique_leagues_map[key] = league_data
            leagues_to_upsert = list(unique_leagues_map.values())
            logger.info(f"Filtered {len(leagues_to_upsert)} raw entries down to {len(leagues_to_upsert)} unique (league_id, season) entries.")

            if leagues_to_upsert:
                total_items = len(leagues_to_upsert)
                num_batches = math.ceil(total_items / batch_size)
                logger.info(f"Processed {total_items} league/season entries. Starting DB upsert in {num_batches} batches...")

                for i in range(0, total_items, batch_size):
                    batch_num = (i // batch_size) + 1
                    batch_data = leagues_to_upsert[i : i + batch_size]
                    logger.debug(f"Upserting batch {batch_num}/{num_batches} ({len(batch_data)} items)...")

                    try:
                        count_in_batch = await league_repo.bulk_upsert_leagues(batch_data)
                        total_entries_submitted += count_in_batch
                        logger.debug(f"Batch {batch_num}/{num_batches} upsert finished. Processed approx: {count_in_batch}")
                    except Exception as batch_error:
                        logger.exception(f"Error upserting batch {batch_num}. Data count: {len(batch_data)}. Error: {batch_error}")
                        raise batch_error

                logger.info(f"League update process finished. Total processed/attempted entries across all batches: ~{total_entries_submitted}")
                return total_entries_submitted

            else:
                logger.info("No valid league/season data to upsert after processing.")
                return 0

        except Exception as e:
            logger.exception(f"Failed during league update process (API fetch or batching logic): {type(e).__name__}")
            raise e

