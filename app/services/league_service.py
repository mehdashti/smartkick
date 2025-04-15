# app/services/league_service.py

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
import math 
from app.core.config import settings

# وارد کردن کلاینت API و ریپازیتوری ها
from app.api_clients import api_football
from app.repositories.league_repository import LeagueRepository
from app.repositories.country_repository import CountryRepository # برای یافتن country_id

# (وارد کردن اسکیماها اگر لازم باشد، فعلا برای update لازم نیست)
# from app.schemas.league import LeagueOut, LeagueCreate

logger = logging.getLogger(__name__)

class LeagueService:
    """
    سرویس برای مدیریت داده های لیگ‌ها.
    شامل منطق واکشی از API، پردازش داده‌ها، و ذخیره‌سازی در دیتابیس.
    """

    async def update_leagues_from_api(
        self,
        db: AsyncSession,
        batch_size: int = settings.DEFAULT_DB_BATCH_SIZE 
    ) -> int:

        """
        لیگ‌ها و فصل‌های آن‌ها را از API خارجی دریافت کرده و در دیتابیس Upsert می‌کند.

        Args:
            db: Session فعال دیتابیس آسنکرون.

        Returns:
            تعداد لیگ/فصل‌هایی که با موفقیت پردازش و برای ذخیره‌سازی ارسال شدند.

        Raises:
            Exception: اگر خطایی در ارتباط با API خارجی، پردازش داده،
                       یافتن کشور یا نوشتن در دیتابیس رخ دهد.
        """
        logger.info(f"Starting leagues update process... (batch size: {batch_size})")
        league_repo = LeagueRepository(db)
        country_repo = CountryRepository(db) # برای جستجوی کشور
        total_entries_submitted = 0
        leagues_to_upsert: List[Dict[str, Any]] = []

        try:
            # 1. دریافت لیست لیگ‌ها از API خارجی
            logger.debug("Fetching leagues from external API...")
            raw_league_entries = await api_football.fetch_leagues_from_api()

            if not raw_league_entries:
                logger.warning("Received empty list of league entries from API. No update performed.")
                return 0

            logger.debug(f"Fetched {len(raw_league_entries)} raw league entries from API. Processing...")

            # 2. پردازش هر لیگ و فصل‌های آن
            for entry in raw_league_entries:
                league_info = entry.get('league', {})
                country_info = entry.get('country', {})
                seasons_info = entry.get('seasons', [])

                if not league_info or not country_info or not seasons_info or not league_info.get('id'):
                    logger.warning(f"Skipping invalid league entry: missing league, country, seasons or league id. Entry: {entry}")
                    continue

                external_league_id = league_info.get('id')
                league_name = league_info.get('name')
                league_type = league_info.get('type')
                league_logo = league_info.get('logo')

                # یافتن کشور مربوطه در دیتابیس ما
                country_code = country_info.get('code')
                country = await country_repo.get_country_by_code(country_code)

                if not country:
                    # اگر کشور در دیتابیس ما نباشد، این لیگ را رد می کنیم
                    # یا می توانید منطق دیگری اعمال کنید (مثلا ایجاد کشور جدید اگر داده کافی باشد)
                    logger.warning(f"Skipping league '{league_name}' (ID: {external_league_id}): Country code '{country_code}' not found in DB.")
                    continue

                # پردازش هر فصل برای این لیگ
                for season_data in seasons_info:
                    season_year = season_data.get('year')
                    start_date_str = season_data.get('start')
                    end_date_str = season_data.get('end')
                    is_current = season_data.get('current', False)
                    coverage = season_data.get('coverage', {})
                    fixtures_coverage = coverage.get('fixtures', {}) # برای دسترسی آسانتر

                    # بررسی وجود داده های ضروری فصل
                    if not all([season_year, start_date_str, end_date_str]):
                         logger.warning(f"Skipping season for league '{league_name}' (ID: {external_league_id}): Missing year, start_date, or end_date. Data: {season_data}")
                         continue

                    # تبدیل تاریخ ها از رشته به آبجکت date
                    try:
                        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        logger.warning(f"Skipping season {season_year} for league '{league_name}' (ID: {external_league_id}): Invalid date format. Start: '{start_date_str}', End: '{end_date_str}'")
                        continue

                    # ساخت دیکشنری داده برای ارسال به ریپازیتوری
                    league_season_dict = {
                        "external_id": external_league_id,
                        "season": season_year,
                        "name": league_name,
                        "country_id": country.country_id, # ID داخلی کشور
                        "type": league_type,
                        "start_date": start_date,
                        "end_date": end_date,
                        "is_current": is_current,
                        "logo_url": league_logo,
                        # استخراج فلگ های Coverage
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

                                # ---> شروع: حذف تکراری ها بر اساس (external_id, season) <---
            # از یک دیکشنری برای نگه داشتن آخرین رکورد برای هر کلید ترکیبی استفاده می کنیم
            unique_leagues_map: Dict[tuple[int, int], Dict[str, Any]] = {}
            for league_data in leagues_to_upsert:
                # کلید ترکیبی external_id و season است
                key = (league_data.get("external_id"), league_data.get("season"))
                # فقط اگر کلید معتبر است (هر دو مقدار دارند)
                if key[0] is not None and key[1] is not None:
                     # آخرین رکورد برای این کلید، رکورد قبلی را بازنویسی می کند
                     unique_leagues_map[key] = league_data

            # تبدیل مقادیر دیکشنری به لیست نهایی بدون تکرار کلید
            leagues_to_upsert = list(unique_leagues_map.values())
            logger.info(f"Filtered {len(leagues_to_upsert)} raw entries down to {len(leagues_to_upsert)} unique (external_id, season) entries.")
            # ---> پایان: حذف تکراری ها <---


            # 3. ارسال داده های پردازش شده به ریپازیتوری به صورت دسته‌ای
            if leagues_to_upsert:
                total_items = len(leagues_to_upsert)
                num_batches = math.ceil(total_items / batch_size)
                logger.info(f"Processed {total_items} league/season entries. Starting DB upsert in {num_batches} batches...")

                for i in range(0, total_items, batch_size):
                    batch_num = (i // batch_size) + 1
                    batch_data = leagues_to_upsert[i : i + batch_size]
                    logger.debug(f"Upserting batch {batch_num}/{num_batches} ({len(batch_data)} items)...")

                    try:
                        # --- فراخوانی ریپازیتوری برای هر بچ ---
                        # هر فراخوانی bulk_upsert_leagues حالا درون تراکنش خودش (در روش ۱)
                        # یا درون تراکنش کلی وابستگی (در روش ۲) اجرا می شود.
                        # مهم است که ریپازیتوری دیگر begin() نداشته باشد اگر از روش ۲ استفاده می کنید.
                        count_in_batch = await league_repo.bulk_upsert_leagues(batch_data)
                        total_entries_submitted += count_in_batch # یا += len(batch_data) بر اساس خروجی ریپازیتوری
                        logger.debug(f"Batch {batch_num}/{num_batches} upsert finished. Processed approx: {count_in_batch}")
                    except Exception as batch_error:
                        # اگر خطایی در یک بچ رخ داد، آن را لاگ کرده و به پردازش ادامه دهیم
                        # یا تصمیم بگیریم کل عملیات را متوقف کنیم (با raise)
                        logger.exception(f"Error upserting batch {batch_num}. Data count: {len(batch_data)}. Error: {batch_error}")
                        raise batch_error # <--- اگر می خواهید با اولین خطای بچ متوقف شوید
                        # اگر می خواهید ادامه دهید، این خطا را raise نکنید

                logger.info(f"League update process finished. Total processed/attempted entries across all batches: ~{total_entries_submitted}")
                return total_entries_submitted # برگرداندن تعداد کل پردازش شده

            else:
                logger.info("No valid league/season data to upsert after processing.")
                return 0

        except Exception as e:
            logger.exception(f"Failed during league update process (API fetch or batching logic): {type(e).__name__}")
            raise e
        
    # می توانید سرویس هایی برای خواندن لیگ ها هم اضافه کنید
    # async def get_league_details(self, league_id: int, db: AsyncSession) -> Optional[LeagueOut]:
    #     ...

