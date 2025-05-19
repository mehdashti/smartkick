# app/services/team_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple, Set
import logging
import math


from app.api_clients import api_football
from app.repositories.venue_repository import VenueRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.country_repository import CountryRepository
from app.services.venue_service import VenueService
from app.models import Team as DBTeam
from app.core.config import settings


logger = logging.getLogger(__name__)

class TeamService:
    """سرویس جامع مدیریت تیم‌ها و ورزشگاه‌های مرتبط"""

    # ---- متدهای پایه تبدیل داده ----

    def _process_team_data(self, api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تبدیل داده تیم از API به فرمت دیتابیس"""
        if not api_data or not isinstance(api_data.get('id'), int):
            return None
        return {
            "team_id": api_data['id'],
            "name": api_data.get('name'),
            "code": api_data.get('code'),
            "founded": api_data.get('founded'),
            "is_national": api_data.get('national', False),
            "logo_url": api_data.get('logo'),
            "country": api_data.get('country'),
            "venue_id": api_data.get('venue_id'),
        }

    # ---- متدهای کمکی پردازش ----
    async def _process_countries(self, db: AsyncSession, country_names: list[str]) -> list[str]:
        """پردازش لیست کشورها و برگرداندن لیست نام کشورهای جدید"""
        if not country_names:
            return []

        country_repo = CountryRepository(db)
        
        all_countries = await country_repo.get_all_countries()
        existing_names = {country.name for country in all_countries}
        
        new_countries = [name for name in country_names if name not in existing_names]

        if new_countries:
            countries_data = [
                {"name": name, "code": None, "flag_url": None}
                for name in new_countries
            ]
            await country_repo.bulk_upsert_countries(countries_data)
        
        return new_countries
                    
    async def _process_team_entry(
        self,
        db: AsyncSession,
        raw_entries: List[Dict[str, Any]],
    ) -> Tuple[int, int]:

        team_repo = TeamRepository(db)
        venue_repo = VenueRepository(db)
        venue_service = VenueService()

        teams = {}  # {team_api_id: processed_team_data}
        venues = {}  # {venue_api_id: processed_venue_data}
        countries = []  # لیست یونیک کشورها

        for entry in raw_entries:
            # پردازش ورزشگاه
            venue_api_id = None
            if venue_info := entry.get('venue'):
                venue_api_id = venue_info.get('id')
                if isinstance(venue_api_id, int) and venue_api_id not in venues:
                    if processed_venue := venue_service._process_venue_data(venue_info):
                        venues[venue_api_id] = processed_venue

            # پردازش تیم + اتصال به ورزشگاه
            if team_info := entry.get('team'):
                team_api_id = team_info.get('id')
                country = team_info.get('country')
                if country and country not in countries:  # بررسی وجود کشور و یونیک بودن
                    countries.append(country)
                if isinstance(team_api_id, int) and team_api_id not in teams:
                    if processed_team := self._process_team_data(team_info):
                        # افزودن venue_api_id به داده‌های تیم
                        processed_team['venue_id'] = venue_api_id
                        teams[team_api_id] = processed_team
        # ذخیره در دیتابیس

        updated_venues = await venue_repo.bulk_upsert_venues(list(venues.values()))
        updated_teams = await team_repo.bulk_upsert_teams(list(teams.values()))
        await self._process_countries(db, countries)

        #logger.info(f"Teams: {updated_teams}, Venues: {updated_venues}")
        return #(updated_teams, updated_venues)


    # ---- متدهای اصلی سرویس ----
    async def update_teams_by_country(
        self,
        db: AsyncSession,
        country_name: str,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> int:
        """به‌روزرسانی تیم‌های یک کشور (یا تمام کشورها)"""
        if country_name.lower() == "allcountries":
            return await self._update_all_countries(db, batch_size)

        logger.info(f"Updating teams for country: {country_name}")
        raw_entries = await api_football.fetch_teams_by_country(country_name)
        if not raw_entries:
            return 0

        teams = await self._process_team_entry(db, raw_entries)
        return (teams)

    async def update_teams_by_league_season(
        self,
        db: AsyncSession,
        league_id: int,
        season: int,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, int]:
        """به‌روزرسانی تیم‌های یک لیگ/فصل"""
        logger.info(f"Updating teams for league={league_id}, season={season}")

        raw_entries = await api_football.fetch_teams_by_league_season(league_id, season)
        if not raw_entries:
            return (0, 0)  # (تعداد تیم‌ها, تعداد ورزشگاه‌ها)

        teams = await self._process_team_entry(db, raw_entries)
        return (teams)


    async def update_team_by_id(
        self,
        db: AsyncSession,
        team_id: int
    ) -> Tuple[int, int]:
        """به‌روزرسانی یک تیم خاص"""
        logger.info(f"Updating single team: {team_id}")
        api_data = await api_football.fetch_team_by_id(team_id)
        if not api_data:
            return (0, 0)

        teams = await self._process_team_entry(db, api_data)
        return (teams)

    # ---- متدهای کمکی ----
    async def _update_all_countries(
        self,
        db: AsyncSession,
        batch_size: int
    ) -> Tuple[int, List[str]]:
        """به‌روزرسانی تیم‌های تمام کشورها"""
        logger.info("Starting update for ALL countries")
        countries = await CountryRepository(db).get_all_countries()
        failed = []
        total = 0

        for country in countries:
            try:
                count = await self.update_teams_by_country(db, country.name, batch_size)
                total += count
            except Exception as e:
                logger.error(f"Failed for {country.name}: {e}")
                failed.append(country.name)

        return total, failed


# نمونه singleton برای استفاده آسان
team_service = TeamService()