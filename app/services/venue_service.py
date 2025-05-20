# app/services/venue_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import logging
from app.repositories.venue_repository import VenueRepository
from app.api_clients import api_football

logger = logging.getLogger(__name__)

class VenueService:
    """
    سرویس برای مدیریت داده‌های ورزشگاه‌ها.
    """

    def _process_venue_data(self, venue_api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
 
        venue_id = venue_api_data.get('id')
        if not venue_api_data or not isinstance(venue_id, int):
            logger.warning(f"Skipping invalid venue data (missing or invalid id): {venue_api_data}")
            return None

        return {
            "venue_id": venue_id,
            "name": venue_api_data.get('name'),
            "address": venue_api_data.get('address'),
            "city": venue_api_data.get('city'),
            "capacity": venue_api_data.get('capacity'),
            "surface": venue_api_data.get('surface'),
            "image_url": venue_api_data.get('image'),
        }

    async def update_venue_by_id(self, db: AsyncSession, venue_id: int) -> bool:
        """
        یک ورزشگاه را با ID اصلی آن از API دریافت کرده و در دیتابیس Upsert می‌کند.
        """
        logger.info(f"Starting venue update process for ID: {venue_id}")
        venue_repo = VenueRepository(db)

        venue_api_data = await api_football.fetch_venue_by_id(venue_id)
        if not venue_api_data:
            logger.warning(f"No venues found from API for id: '{venue_id}'. No update performed.")
            return False

        # بررسی اینکه venue_api_data یک دیکشنری است
        if not isinstance(venue_api_data, dict):
            logger.error(f"Expected dict, got {type(venue_api_data)}: {venue_api_data}")
            return False

        # پردازش داده venue
        processed_venue = self._process_venue_data(venue_api_data) if venue_api_data.get("id") else None

        if not processed_venue:
            logger.warning(f"No valid venue data to upsert for id: '{venue_id}'")
            return False

        # Upsert تک venue
        updated_count = await venue_repo.bulk_upsert_venues([processed_venue])
        logger.info(f"Successfully updated {updated_count} venues for id: '{venue_id}'")
        return True


    async def update_venues_by_country(self, db: AsyncSession, country_name: str) -> int:
        """
        ورزشگاه‌ها را برای یک کشور مشخص از API دریافت کرده و در دیتابیس Upsert می‌کند.
        """
        logger.info(f"Starting venues update process for country: '{country_name}'")
        venue_repo = VenueRepository(db)

        venues_api_data = await api_football.fetch_venues_by_country(country_name)
        if not venues_api_data:
            logger.warning(f"No venues found from API for country: '{country_name}'. No update performed.")
            return 0

        processed_venues = [
            self._process_venue_data(venue)
            for venue in venues_api_data if venue.get("id")
        ]

        processed_venues = [venue for venue in processed_venues if venue]
        if not processed_venues:
            logger.warning(f"No valid venue data to upsert for country: '{country_name}'")
            return 0

        updated_count = await venue_repo.bulk_upsert_venues(processed_venues)
        logger.info(f"Successfully updated {updated_count} venues for country: '{country_name}'")
        return updated_count

