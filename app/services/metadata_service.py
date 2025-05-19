# app/services/metadata_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import logging
from app.repositories.country_repository import CountryRepository
from app.repositories.timezone_repository import TimezoneRepository
from app.api_clients import api_football

logger = logging.getLogger(__name__)

class MetadataService:

    def _process_country_data(self, country_api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "name": country_api_data.get('name'),
            "code": country_api_data.get('code'),
            "flag_url": country_api_data.get('flag'),
        }

    async def update_country(self, db: AsyncSession) -> int:

        logger.info(f"Starting country update process")
        country_repo = CountryRepository(db)

        country_api_data = await api_football.fetch_countries_from_api()
        if not country_api_data:
            logger.warning(f"No country found from API. No update performed.")
            return 0

        processed_countries = [
            self._process_country_data(country)
            for country in country_api_data if country.get("name")
        ]

        processed_countries = [country for country in processed_countries if country]
        if not processed_countries:
            logger.warning(f"No valid country data to upsert.")
            return 0        

        updated_count = await country_repo.bulk_upsert_countries(processed_countries)
        logger.info(f"Successfully updated {updated_count} countries")
        return updated_count


    async def update_timezone(self, db: AsyncSession):#-> Dict[str, any]:
        logger.info("Starting timezone update process")
        timezone_repo = TimezoneRepository(db)

        api_response = await api_football.fetch_timezones_from_api()
        if not api_response:
            logger.warning("No timezone data received from API")
            return 0

        updated_count = await timezone_repo.bulk_upsert_timezones(api_response)
        logger.info(f"Updated {updated_count} timezones")
        return updated_count
