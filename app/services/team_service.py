# app/services/team_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple # Tuple را اضافه کنید
import logging
import math

# وارد کردن کلاینت API و ریپازیتوری‌ها
from app.api_clients import api_football
from app.repositories.venue_repository import VenueRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.country_repository import CountryRepository
from app.core.config import settings # برای batch_size
# مدل‌ها برای type hint (اختیاری ولی مفید)
from app.models.country import Country as DBCountry
from app.models.venue import Venue as DBVenue
from app.models.team import Team as DBTeam


logger = logging.getLogger(__name__)

class TeamService:
    """
    سرویس برای مدیریت داده‌های تیم‌ها و ورزشگاه‌های مرتبط.
    شامل واکشی از API، پردازش و ذخیره‌سازی در دیتابیس.
    """

    # --- Helper Methods for Mapping Data ---

    def _map_api_venue_to_db(self, api_venue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تبدیل داده‌های ورزشگاه API به فرمت دیکشنری برای ذخیره در دیتابیس."""
        if not api_venue_data or not isinstance(api_venue_data.get('id'), int):
            return None
        return {
            "external_id": api_venue_data['id'],
            "name": api_venue_data.get('name'),
            "address": api_venue_data.get('address'),
            "city": api_venue_data.get('city'),
            "capacity": api_venue_data.get('capacity'),
            "surface": api_venue_data.get('surface'),
            "image_url": api_venue_data.get('image'),
        }

    def _map_api_team_to_db(self, api_team_data: Dict[str, Any], country_id: int, venue_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """تبدیل داده‌های تیم API به فرمت دیکشنری برای ذخیره در دیتابیس."""
        if not api_team_data or not isinstance(api_team_data.get('id'), int):
            return None
        return {
            "external_id": api_team_data['id'],
            "name": api_team_data.get('name'),
            "code": api_team_data.get('code'),
            "founded": api_team_data.get('founded'),
            "is_national": api_team_data.get('national', False),
            "logo_url": api_team_data.get('logo'),
            "country_id": country_id, # ID داخلی کشور (از پارامتر ورودی)
            "venue_id": venue_id,     # ID داخلی ورزشگاه (از پارامتر ورودی)
        }

    # --- Main Service Method for Single Country ---

    async def update_teams_by_country(
        self,
        db: AsyncSession,
        country_name: str, # نام کشور استفاده شده برای فراخوانی API
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> int:
        """
        تیم‌ها و ورزشگاه‌ها را برای یک کشور خاص از API دریافت و در دیتابیس Upsert می‌کند.
        از نام کشور ورودی (`country_name`) برای پیدا کردن country_id استفاده می‌کند.

        Args:
            db: Session فعال دیتابیس.
            country_name: نام کشوری که برای درخواست به API استفاده شده است.
            batch_size: اندازه بچ برای عملیات bulk upsert.

        Returns:
            تعداد رکوردهای تیم که با موفقیت پردازش و برای ذخیره‌سازی ارسال شدند.

        Raises:
            ValueError: اگر کشور ورودی (`country_name`) در دیتابیس محلی یافت نشود.
            Exception: سایر خطاهای API یا دیتابیس.
        """
        logger.info(f"Starting team/venue update for country: '{country_name}'")
        venue_repo = VenueRepository(db)
        team_repo = TeamRepository(db)
        country_repo = CountryRepository(db)
        total_teams_submitted = 0
        teams_to_upsert: List[Dict[str, Any]] = []

        # 1. پیدا کردن کشور در دیتابیس *قبل* از فراخوانی API
        # این اطمینان می‌دهد که ما یک country_id معتبر برای استفاده داریم.
        db_country: Optional[DBCountry] = await country_repo.get_country_by_name(country_name)
        if not db_country:
            logger.error(f"CRITICAL: Cannot process teams for '{country_name}'. Country not found in local DB.")
            raise ValueError(f"Country '{country_name}' not found in local database.")
        target_country_id = db_country.country_id
        logger.debug(f"Found country '{country_name}' in DB with ID: {target_country_id}")

        try:
            # 2. دریافت داده‌های خام از API با استفاده از country_name
            logger.debug(f"Fetching teams/venues from API for country: {country_name}")
            raw_entries: List[Dict[str, Any]] = await api_football.fetch_teams_by_country(country_name)

            if not raw_entries:
                logger.warning(f"Received no valid team entries from API for country: {country_name}.")
                return 0

            logger.debug(f"Fetched {len(raw_entries)} raw team/venue entries. Processing...")

            # 3. پردازش هر رکورد (تیم + ورزشگاه)
            processed_external_ids = set() # برای جلوگیری از پردازش تکراری تیم در یک اجرا
            for entry in raw_entries:
                api_team = entry.get('team')
                api_venue = entry.get('venue')

                # اعتبارسنجی اولیه داده تیم
                if not api_team or api_team.get('id') is None:
                    logger.warning(f"Skipping entry due to missing or invalid team data: {entry}")
                    continue

                team_external_id = api_team['id']
                # اگر این ID تیم قبلا پردازش شده، رد کن
                if team_external_id in processed_external_ids:
                    logger.debug(f"Skipping duplicate team external_id {team_external_id} in this run.")
                    continue
                processed_external_ids.add(team_external_id)

                # --- پردازش و Upsert ورزشگاه ---
                venue_id: Optional[int] = None
                if api_venue and api_venue.get('id') is not None:
                    venue_data_to_upsert = self._map_api_venue_to_db(api_venue)
                    if venue_data_to_upsert:
                        try:
                            # Upsert ورزشگاه و گرفتن آبجکت ذخیره شده
                            db_venue: DBVenue = await venue_repo.upsert_venue(venue_data_to_upsert)
                            venue_id = db_venue.venue_id
                        except Exception as venue_error:
                            logger.error(f"!!! Failed to upsert venue (External ID: {api_venue.get('id')}). Error Type: {type(venue_error).__name__}, Details: {venue_error}", exc_info=True)
                            venue_id = None # همچنان None می‌گذاریم
                    else:
                        logger.warning(f"Could not map venue data for team {team_external_id}. Venue data: {api_venue}")
                else:
                     logger.debug(f"No venue data provided for team {team_external_id}.")

                # --- آماده‌سازی داده تیم با استفاده از target_country_id ---
                # دیگر نیازی به جستجوی کشور بر اساس نام API نیست
                team_data_to_upsert = self._map_api_team_to_db(api_team, target_country_id, venue_id)
                if team_data_to_upsert:
                    teams_to_upsert.append(team_data_to_upsert)
                else:
                    logger.warning(f"Could not map team data for external_id {team_external_id}. Team data: {api_team}")

            # 4. ارسال تیم‌های پردازش شده به ریپازیتوری به صورت دسته‌ای
            if teams_to_upsert:
                total_items = len(teams_to_upsert)
                num_batches = math.ceil(total_items / batch_size)
                logger.info(f"Processed {total_items} valid team entries for '{country_name}'. Starting DB upsert in {num_batches} batches...")

                for i in range(0, total_items, batch_size):
                    batch_num = (i // batch_size) + 1
                    batch_data = teams_to_upsert[i : i + batch_size]
                    logger.debug(f"Upserting team batch {batch_num}/{num_batches} ({len(batch_data)} items)...")
                    try:
                        # --- فراخوانی ریپازیتوری برای هر بچ ---
                        count_in_batch = await team_repo.bulk_upsert_teams(batch_data)
                        total_teams_submitted += count_in_batch # یا len(batch_data)
                        logger.debug(f"Team Batch {batch_num}/{num_batches} upsert finished. Processed approx: {count_in_batch}")
                    except Exception as batch_error:
                        logger.exception(f"Error upserting team batch {batch_num} for country '{country_name}'. Data count: {len(batch_data)}. Error: {batch_error}")
                        # در این حالت، چون در یک تراکنش هستیم، کل عملیات برای این کشور rollback خواهد شد
                        raise batch_error # خطا را دوباره raise کن تا rollback توسط begin_nested یا begin اصلی انجام شود

                logger.info(f"Team/Venue update process finished successfully for country '{country_name}'. Total teams submitted/processed: ~{total_teams_submitted}")
                return total_teams_submitted

            else:
                logger.info(f"No valid team data to upsert after processing for country '{country_name}'.")
                return 0

        except (ConnectionError, TimeoutError, ValueError, LookupError) as known_error:
             # خطاهای API یا ValueError از پیدا نشدن کشور در ابتدا
             logger.error(f"Failed during team update process for country '{country_name}': {type(known_error).__name__} - {known_error}", exc_info=True)
             raise known_error # ارسال مجدد برای مدیریت در لایه بالاتر
        except Exception as e:
             # خطاهای غیرمنتظره دیگر (مثل خطای DB در bulk upsert)
             logger.exception(f"Unexpected error during team update process for country '{country_name}': {type(e).__name__}")
             raise RuntimeError(f"An unexpected error occurred during team update for {country_name}: {e}") from e

    # --- Main Service Method for All Countries ---

    async def update_teams_for_all_countries(
        self,
        db: AsyncSession,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE
    ) -> Tuple[int, List[str]]:
        """
        فرآیند به‌روزرسانی تیم‌ها و ورزشگاه‌ها را برای *تمام* کشورهای موجود در دیتابیس اجرا می‌کند.
        از تراکنش‌های تودرتو برای ایزوله کردن خطاها استفاده می‌کند.

        Returns:
            یک tuple شامل:
            - تعداد کل تیم‌هایی که در تمام کشورها با موفقیت پردازش شدند.
            - لیستی از نام کشورهایی که در فرآیند به‌روزرسانی آن‌ها خطا رخ داده است.
        """
        logger.info("Starting team/venue update process for ALL countries.")
        country_repo = CountryRepository(db)
        total_processed_count = 0
        failed_countries: List[str] = []

        try:
            # 1. گرفتن لیست همه کشورها
            all_countries = await country_repo.get_all_countries(limit=1000) # یا تابع شما

            if not all_countries:
                logger.warning("No countries found in the database. Cannot update for all countries.")
                return 0, []

            logger.info(f"Found {len(all_countries)} countries. Starting updates with nested transactions...")

            # 2. اجرای آپدیت برای هر کشور در یک تراکنش تودرتو (SAVEPOINT)
            for i, country in enumerate(all_countries):
                # --- استفاده از نام کشور از دیتابیس خودمان ---
                country_name_from_db = country.name
                logger.info(f"--- Processing country {i+1}/{len(all_countries)}: '{country_name_from_db}' ---")

                try:
                    # شروع یک SAVEPOINT جدید
                    async with db.begin_nested():
                        # فراخوانی متد آپدیت برای تک کشور با نام از دیتابیس ما
                        count_for_country = await self.update_teams_by_country(
                            db=db,
                            country_name=country_name_from_db, # <--- استفاده از نام کشور DB
                            batch_size=batch_size
                        )
                        total_processed_count += count_for_country
                        logger.info(f"--- Successfully processed country '{country_name_from_db}'. Teams processed: {count_for_country} ---")
                    # RELEASE SAVEPOINT در صورت موفقیت

                except ValueError as ve: # خطای پیدا نشدن کشور (که نباید اینجا رخ دهد) یا خطای دیگر از update_teams_by_country
                     logger.error(f"!!! Value error processing country '{country_name_from_db}'. Error: {ve}", exc_info=False)
                     failed_countries.append(country_name_from_db)
                except Exception as country_error:
                    # سایر خطاها -> ROLLBACK TO SAVEPOINT
                    logger.error(f"!!! Failed to update teams for country '{country_name_from_db}'. Rolling back changes for this country. Error: {type(country_error).__name__} - {country_error}", exc_info=True) # لاگ کامل
                    failed_countries.append(country_name_from_db)
                    # ادامه حلقه

            logger.info("Finished team/venue update process for ALL countries.")
            logger.info(f"Total teams processed across all successful countries: {total_processed_count}")
            if failed_countries:
                logger.warning(f"Updates failed for the following countries: {', '.join(failed_countries)}")

            return total_processed_count, failed_countries

        except Exception as e:
            logger.exception("An unexpected error occurred during the 'update all countries' outer process.")
            return total_processed_count, failed_countries # یا raise خطا