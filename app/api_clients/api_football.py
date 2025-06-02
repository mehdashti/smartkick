# app/api_clients/api_football.py
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
# فرض بر این است که redis_client یک نمونه از redis.asyncio.Redis است
# مثال:
# import redis.asyncio as redis
# redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
from app.core.redis import redis_client # مطمئن شوید این یک کلاینت ناهمگام است
import logging
import asyncio
import random
# از قفل ناهمگام redis-py استفاده کنید (برای نسخه >= 4.2)
from redis.asyncio.lock import Lock as AsyncLock # تغییر نام به AsyncLock برای وضوح
import redis.exceptions # برای مدیریت خطاهای قفل

logger = logging.getLogger(__name__)

BASE_URL = f"https://{settings.API_FOOTBALL_HOST}"
HEADERS = {
    'x-rapidapi-host': settings.API_FOOTBALL_HOST,
    'x-rapidapi-key': settings.API_FOOTBALL_KEY
}
DEFAULT_TIMEOUT = 15.0

# --- Rate Limiting Settings ---
# استفاده مستقیم از متغیرهای settings برای خوانایی بهتر
_RATE_LIMIT_KEY = "api_football:rate_limit"
_LOCK_NAME = "api_football:lock"

async def _wait_for_rate_limit_async(): # تغییر نام و تبدیل به async
    """Checks and waits for the rate limit using Redis before making a request (async version)."""
    max_attempts_loop = 15  # تعداد تلاش برای گرفتن اسلات در حلقه اصلی
    lock_acquire_timeout = 0.2  # حداکثر زمان انتظار برای به دست آوردن قفل (ثانیه)
    lock_instance_timeout = 10  # حداکثر زمانی که قفل نگه داشته می‌شود (ثانیه) - باید بیشتر از عملیات Redis باشد

    # زمان انتظار اولیه، در صورت عدم موفقیت در کسب قفل یا رسیدن به محدودیت، افزایش می‌یابد
    current_retry_wait = 0.1

    for attempt in range(max_attempts_loop):
        slot_acquired_this_iteration = False
        calculated_sleep_if_limited = 1.0 # زمان پیش‌فرض انتظار اگر به محدودیت برسیم

        try:
            async with AsyncLock(redis_client, _LOCK_NAME, timeout=lock_instance_timeout, blocking_timeout=lock_acquire_timeout):
                # قفل با موفقیت به دست آمد
                pipe = redis_client.pipeline()
                pipe.get(_RATE_LIMIT_KEY)
                pipe.ttl(_RATE_LIMIT_KEY)
                current_requests_str, ttl_seconds = await pipe.execute()

                current_requests = int(current_requests_str or 0)
                # ttl: -2 اگر کلید وجود نداشته باشد، -1 اگر کلید وجود داشته باشد ولی تاریخ انقضا نداشته باشد
                ttl = int(ttl_seconds or -2)

                # بررسی و اصلاح وضعیت‌های نامعتبر
                if ttl == -2 and current_requests > 0: # شمارنده وجود دارد ولی کلید منقضی شده/حذف شده
                    logger.warning(f"Rate limit key {_RATE_LIMIT_KEY} had count {current_requests} but was missing/expired. Resetting count.")
                    # این حالت نباید رخ دهد اگر expire به درستی ست شود، اما برای اطمینان
                    await redis_client.set(_RATE_LIMIT_KEY, 0, ex=settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS)
                    current_requests = 0
                    ttl = settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS
                elif ttl == -1 and current_requests > 0: # شمارنده وجود دارد ولی تاریخ انقضا ندارد
                    logger.warning(f"Rate limit key {_RATE_LIMIT_KEY} was permanent. Setting expiry {settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS}s.")
                    await redis_client.expire(_RATE_LIMIT_KEY, settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS)
                    ttl = settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS
                elif ttl == 0 : # کلید همین الان منقضی شده
                    current_requests = 0


                if current_requests < settings.API_FOOTBALL_MAX_REQUESTS_PER_MINUTE:
                    # می‌توانیم درخواست ارسال کنیم
                    p_incr = redis_client.pipeline()
                    p_incr.incr(_RATE_LIMIT_KEY)
                    # همیشه تاریخ انقضا را تنظیم/به‌روزرسانی می‌کنیم
                    # اگر INCR کلید را ایجاد کند، EXPIRE آن را تنظیم می‌کند. اگر کلید وجود داشته باشد، EXPIRE آن را به‌روزرسانی می‌کند.
                    p_incr.expire(_RATE_LIMIT_KEY, settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS)
                    new_count_results = await p_incr.execute()
                    new_count = new_count_results[0] # INCR نتیجه را در یک لیست برمی‌گرداند

                    logger.debug(f"Rate limit slot acquired. Current count: {new_count}/{settings.API_FOOTBALL_MAX_REQUESTS_PER_MINUTE}")
                    slot_acquired_this_iteration = True
                else:
                    # به محدودیت نرخ رسیده‌ایم
                    logger.warning(
                        f"Rate limit reached ({current_requests}/{settings.API_FOOTBALL_MAX_REQUESTS_PER_MINUTE}). "
                        f"TTL: {ttl if ttl > 0 else settings.API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS}s."
                    )
                    if ttl > 0:
                        # اگر TTL معتبر است، حداقل به اندازه آن یا بخشی از آن صبر می‌کنیم
                        calculated_sleep_if_limited = max(0.2, min(float(ttl), 5.0)) # حداکثر 5 ثانیه یا TTL صبر کن
                    else: # TTL نامعتبر است (منفی) یا 0
                        # این یعنی پنجره باید ریست شده باشد. یک انتظار کوتاه اعمال می‌کنیم.
                        calculated_sleep_if_limited = 0.5
            # قفل در اینجا آزاد می‌شود (با خروج از بلاک 'with')

            if slot_acquired_this_iteration:
                return True # موفقیت‌آمیز

            # اگر اسلات در دسترس نبود (محدودیت نرخ)، به مدت calculated_sleep_if_limited صبر می‌کنیم
            logger.info(f"Rate limit active or lock contention. Sleeping for {calculated_sleep_if_limited:.2f}s before retrying.")
            await asyncio.sleep(calculated_sleep_if_limited + random.uniform(0, 0.1)) # jitter اضافه می‌کنیم
            current_retry_wait = min(current_retry_wait * 1.5, 5.0) # افزایش زمان انتظار برای تلاش بعدی

        except redis.exceptions.LockError: # یا TimeoutError اگر blocking_timeout در AsyncLock منقضی شود
            logger.warning(f"Attempt {attempt + 1}: Could not acquire Redis lock for rate limiting. Retrying after {current_retry_wait:.2f}s.")
            await asyncio.sleep(current_retry_wait + random.uniform(0, 0.05))
            current_retry_wait = min(current_retry_wait * 1.5, 3.0)  # افزایش زمان انتظار برای قفل
        except redis.RedisError as e:
            logger.error(f"Attempt {attempt + 1}: Redis error during rate limiting: {e}. Retrying after {current_retry_wait:.2f}s.")
            await asyncio.sleep(current_retry_wait + random.uniform(0, 0.1))
            current_retry_wait = min(current_retry_wait * 1.5, 10.0) # افزایش زمان انتظار برای خطاهای Redis
        except Exception as e:
            logger.exception(f"Attempt {attempt + 1}: Unexpected error in rate limiting: {e}. Retrying after {current_retry_wait:.2f}s.")
            await asyncio.sleep(current_retry_wait + random.uniform(0, 0.1))
            current_retry_wait = min(current_retry_wait * 1.5, 10.0)

    logger.error("Failed to pass rate limit check after maximum attempts.")
    return False

async def _make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    expected_status: int = 200
) -> Dict[str, Any]:
    """Makes a rate-limited request to the API-Football endpoint (async version)."""
    max_retries = 5
    base_retry_delay = 1.0  # زمان تاخیر پایه برای تلاش مجدد
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(max_retries):
        # بررسی محدودیت نرخ به صورت ناهمگام
        if not await _wait_for_rate_limit_async(): # <<< تغییر کلیدی: فراخوانی نسخه async
            # اگر _wait_for_rate_limit_async پس از چندین تلاش ناموفق بود،
            # در اینجا یک خطا ایجاد می‌کنیم یا پس از یک تاخیر طولانی‌تر دوباره تلاش می‌کنیم.
            # در حال حاضر، فرض بر این است که اگر false برگرداند، باید درخواست را متوقف کنیم.
            logger.error(f"Rate limit check failed definitively for {url}. Aborting request.")
            raise ValueError(f"API Error: Failed to pass rate limit check for {url}.")

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            try:
                current_delay = base_retry_delay * (2 ** attempt) + random.uniform(0, 0.5) # Exponential backoff with jitter

                logger.debug(f"Sending API request (Attempt {attempt + 1}/{max_retries}): {method} {url} Params: {params}")
                response = await client.request(
                    method=method,
                    url=url,
                    headers=HEADERS,
                    params=params
                )

                if response.status_code == 429: # Too Many Requests
                    logger.warning(f"Received 429 Too Many Requests from {url}. Retrying after {current_delay:.2f} seconds.")
                    # این کد وضعیت معمولاً به این معنی است که محدودیت نرخ خود API (نه محدودیت ما) فعال شده است.
                    # شاید لازم باشد منطق _wait_for_rate_limit_async را بازبینی کنیم یا یک کلید جداگانه برای 429 داشته باشیم.
                    # فعلا فقط صبر می‌کنیم و دوباره تلاش می‌کنیم.
                    await asyncio.sleep(current_delay)
                    continue

                if response.status_code != expected_status:
                    logger.error(f"API Error: Unexpected status code {response.status_code} from {url}. Body: {response.text[:500]}")
                    # برای خطاهای خاص سرور (5xx) ممکن است بخواهیم دوباره تلاش کنیم
                    if 500 <= response.status_code < 600 and attempt < max_retries - 1 :
                        logger.info(f"Server error {response.status_code}. Retrying after {current_delay:.2f} seconds...")
                        await asyncio.sleep(current_delay)
                        continue
                    raise ValueError(f"API Error: Unexpected status code {response.status_code} from {url}.")

                try:
                    data = response.json()
                    # بررسی خطای محدودیت نرخ در بدنه پاسخ (برخی API ها این کار را می‌کنند)
                    if isinstance(data, dict) and "message" in data and "Too many requests" in data["message"]:
                         logger.warning(f"API rate limit message in response body from {url}. Retrying after {current_delay:.2f} seconds.")
                         await asyncio.sleep(current_delay)
                         continue
                    # در کد شما بود: data.get("rateLimit") == "Too many requests..."
                    # اگر این فرمت دقیق است، آن را نگه دارید.

                    logger.debug(f"Received successful API response ({response.status_code}) from {url}")
                    return data
                except ValueError as json_err: # اگر پاسخ JSON نباشد
                    logger.error(f"API Error: Failed to decode JSON response from {url}. Status: {response.status_code}, Text: {response.text[:500]}")
                    raise ValueError(f"API Error: Failed to decode JSON response from {url}.") from json_err

            except httpx.TimeoutException as e:
                logger.error(f"API Error: Request to {url} timed out after {DEFAULT_TIMEOUT} seconds on attempt {attempt + 1}.") # <<< DEFAULT_TIMEOUT
                if attempt < max_retries - 1:
                    await asyncio.sleep(current_delay)
                    continue
                raise TimeoutError(f"API Error: Request to {url} timed out after {max_retries} attempts.") from e
            except httpx.RequestError as e: # خطاهای شبکه و اتصال
                logger.error(f"API Error: Network error connecting to {url} on attempt {attempt + 1}. Error: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(current_delay)
                    continue
                raise ConnectionError(f"API Error: Network error connecting to {url} ({e}) after {max_retries} attempts.") from e
            # ValueError و Exception های عمومی‌تر در اینجا مدیریت نمی‌شوند تا در صورت بروز، به بالا منتشر شوند.

        # تاخیر کوتاه بین درخواست‌ها (اختیاری، اگر API به آن نیاز دارد)
        # await asyncio.sleep(0.2) # اگر _wait_for_rate_limit_async به درستی کار کند، این ممکن است لازم نباشد.

    logger.error(f"Failed to make API request to {url} after {max_retries} retries.")
    raise ValueError(f"API Error: Max retries exceeded for {url}.")


async def fetch_coach_by_id(coach_id: int) -> Dict[str, Any]:
    """Fetch coach data by ID from API-Football."""
    endpoint = "/coachs"
    params = {"id": coach_id}
    return await _make_api_request("GET", endpoint, params=params)

async def fetch_player_teams(player_id: int) -> Dict[str, Any]:
    """Fetch player teams data from API-Football."""
    endpoint = "/players/teams"
    params = {"player": player_id}
    data = await _make_api_request("GET", endpoint, params=params)
    
    response_list = data.get('response')
    if isinstance(response_list, list) and response_list:
        return response_list[0]
    else:
        raise LookupError(f"Player teams not found or invalid response for ID: {player_id}")
    

async def fetch_timezones_from_api() -> List[str]:
    endpoint = "/timezone"
    data = await _make_api_request("GET", endpoint)

    response_list = data.get('response')
    if isinstance(response_list, list) and all(isinstance(item, str) for item in response_list):
        return response_list
    else:
        raise ValueError(f"Invalid timezone response format: Expected list of strings.")
    

async def fetch_countries_from_api() -> List[Dict[str, Any]]:
    endpoint = "/countries"
    logger.info("Fetching countries from external API...")
    try:
        data = await _make_api_request("GET", endpoint) 

        response_list = data.get('response')
        if isinstance(response_list, list) and all(isinstance(item, dict) for item in response_list):
             valid_countries = [
                 country for country in response_list
                 if isinstance(country.get("name"), str) and isinstance(country.get("code"), str) 
             ]
             logger.info(f"Successfully fetched {len(valid_countries)} valid countries from API.")
             return valid_countries 
        else:
             logger.error(f"Invalid response structure for countries: {data}")

             raise ValueError("Invalid countries response format: Expected list of dicts.")
    except Exception as e:
         logger.error(f"Failed to fetch countries from API: {e}", exc_info=True)

         raise 
    

async def fetch_leagues_from_api() -> List[Dict[str, Any]]:
    endpoint = "/leagues"
    logger.info("Fetching leagues from external API...")
    try:
        data = await _make_api_request("GET", endpoint)
      
        response_list = data.get('response')
        if isinstance(response_list, list) and all(
            isinstance(item, dict) and
            'league' in item and 'country' in item and 'seasons' in item
            for item in response_list
        ):
            logger.info(f"Successfully fetched {len(response_list)} league entries from API.")
            return response_list
        else:
            logger.error(f"Invalid response structure for leagues: {data}")
            raise ValueError("Invalid leagues response format: Expected list of dicts with 'league', 'country', 'seasons'.")

    except Exception as e:
        logger.exception(f"Failed during fetching or initial processing of leagues from API: {e}")
        raise

async def fetch_teams_by_country(country_name: str) -> List[Dict[str, Any]]:
    endpoint = "/teams"
    params = {"country": country_name}
    logger.info(f"Fetching teams from external API for country: {country_name}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        response_list = data.get('response')
        if isinstance(response_list, list):
             valid_entries = [
                 entry for entry in response_list
                 if isinstance(entry, dict) and 'team' in entry and 'venue' in entry
                 and isinstance(entry.get('team'), dict) and entry['team'].get('id') is not None
             ]
             if len(valid_entries) != len(response_list):
                  logger.warning(f"Found {len(response_list) - len(valid_entries)} invalid team entries in API response for {country_name}.")

             logger.info(f"Successfully fetched {len(valid_entries)} valid team entries from API for country: {country_name}")
             return valid_entries
        else:
             logger.error(f"Invalid response structure for teams (country: {country_name}): Expected list under 'response'. Response: {data}")
             return [] 

    except (ValueError, ConnectionError, TimeoutError, LookupError) as api_error:
        logger.error(f"API Error fetching teams for country {country_name}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching teams for country {country_name}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for teams: {e}") from e

# --- بازنویسی تابع fetch_teams_by_league_season ---
async def fetch_teams_by_league_season(league_id: int, season: int) -> List[Dict[str, Any]]:
    """
    تیم‌ها و ورزشگاه‌های مربوط به یک لیگ و فصل خاص را از API دریافت می‌کند.
    (با ساختار مشابه fetch_teams_by_country)
    """
    endpoint = "/teams"
    params = {"league": str(league_id), "season": str(season)}
    logger.info(f"Fetching teams from external API for league_id={league_id}, season={season}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching teams for league={league_id}, season={season}: {data['errors']}")
            return []

        response_list = data.get('response')
        if isinstance(response_list, list):
             # فیلتر کردن ورودی‌های نامعتبر (مشابه قبل)
             valid_entries = [
                 entry for entry in response_list
                 if isinstance(entry, dict) and 'team' in entry and 'venue' in entry
                 and isinstance(entry.get('team'), dict) and entry['team'].get('id') is not None
                 and isinstance(entry.get('venue'), dict)
             ]
             if len(valid_entries) != len(response_list):
                  invalid_count = len(response_list) - len(valid_entries)
                  logger.warning(f"Found {invalid_count} invalid/incomplete team entries in API response for league={league_id}, season={season}. Skipping them.")

             logger.info(f"Successfully fetched {len(valid_entries)} valid team entries from API for league={league_id}, season={season}")
             return valid_entries
        else:
             logger.error(f"Invalid response structure for teams (league={league_id}, season={season}): Expected list under 'response', got {type(response_list)}. Response: {data}")
             return []

    except (ValueError, ConnectionError, TimeoutError) as api_error: # LookupError حذف شد
        logger.error(f"API Error fetching teams for league={league_id}, season={season}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching teams for league={league_id}, season={season}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for teams by league/season: {e}") from e


# --- بازنویسی تابع fetch_venue_by_id ---
async def fetch_venue_by_id(external_venue_id: int) -> Optional[Dict[str, Any]]:
    """
    اطلاعات یک ورزشگاه خاص را بر اساس ID خارجی آن از API دریافت می‌کند.
    (با ساختار مشابه fetch_teams_by_country)
    """
    endpoint = "/venues"
    params = {"id": str(external_venue_id)}
    logger.info(f"Fetching venue from external API for external_id={external_venue_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            # این مورد می‌تواند به معنی 'not found' هم باشد، اما لاگ می‌کنیم
            logger.error(f"API reported errors fetching venue for id={external_venue_id}: {data['errors']}")
            return None # چون انتظار یک آبجکت یا None را داریم

        response_list = data.get('response')
        if isinstance(response_list, list):
            if len(response_list) == 1:
                entry = response_list[0]
                # اعتبارسنجی ورودی تکی
                if isinstance(entry, dict) and entry.get('id') == external_venue_id:
                    logger.info(f"Successfully fetched valid venue entry from API for external_id={external_venue_id}")
                    return entry
                else:
                    logger.warning(f"Received invalid venue entry or ID mismatch for external_id={external_venue_id}. Data: {entry}")
                    return None
            elif len(response_list) == 0:
                 logger.warning(f"Venue with external_id={external_venue_id} not found in API (empty response list).")
                 return None
            else:
                 # انتظار بیش از یک نتیجه برای جستجو با ID نداریم
                 logger.error(f"Unexpected number of results ({len(response_list)}) fetching venue by id={external_venue_id}. Response: {data}")
                 return None # یا اولین مورد معتبر را برگردانید اگر منطقی باشد
        else:
            logger.error(f"Invalid response structure for venue (id={external_venue_id}): Expected list under 'response', got {type(response_list)}. Response: {data}")
            return None

    except (ValueError, ConnectionError, TimeoutError) as api_error: # LookupError حذف شد
        logger.error(f"API Error fetching venue for id={external_venue_id}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching venue for id={external_venue_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for venue by id: {e}") from e


# --- بازنویسی تابع fetch_venues_by_country ---
async def fetch_venues_by_country(country_name: str) -> List[Dict[str, Any]]:
    """
    لیست ورزشگاه‌های یک کشور خاص را از API دریافت می‌کند.
    (با ساختار مشابه fetch_teams_by_country)
    """
    endpoint = "/venues"
    params = {"country": country_name}
    logger.info(f"Fetching venues from external API for country: {country_name}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching venues for country {country_name}: {data['errors']}")
            return []

        response_list = data.get('response')
        if isinstance(response_list, list):
             # فیلتر کردن ورودی‌های نامعتبر (فقط چک می‌کنیم dict باشد و id داشته باشد)
             valid_entries = [
                 entry for entry in response_list
                 if isinstance(entry, dict) and entry.get('id') is not None
             ]
             if len(valid_entries) != len(response_list):
                  invalid_count = len(response_list) - len(valid_entries)
                  logger.warning(f"Found {invalid_count} invalid/incomplete venue entries in API response for country {country_name}. Skipping them.")

             logger.info(f"Successfully fetched {len(valid_entries)} valid venue entries from API for country: {country_name}")
             return valid_entries
        else:
             logger.error(f"Invalid response structure for venues (country: {country_name}): Expected list under 'response', got {type(response_list)}. Response: {data}")
             return []

    except (ValueError, ConnectionError, TimeoutError) as api_error: # LookupError حذف شد
        logger.error(f"API Error fetching venues for country {country_name}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching venues for country {country_name}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for venues by country: {e}") from e
    
    
# --- تابع fetch_player_profiles_from_api با پارامتر page ---
async def fetch_player_profiles_from_api(page: int) -> Optional[Dict[str, Any]]: # <--- اضافه کردن page
    """
    یک صفحه مشخص از پروفایل‌های بازیکنان را از API دریافت می‌کند.
    """
    endpoint = "/players/profiles"
    params = {"page": str(page)} # <--- استفاده از پارامتر page
    logger.info(f"Fetching player profiles from external API (page {page})")
    try:
        # ارسال درخواست به API
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching player profiles (page {page}): {data['errors']}")
            return None

        # بررسی اولیه ساختار پاسخ (بدون تغییر)
        if 'response' not in data or not isinstance(data['response'], list):
            logger.error(f"Invalid response structure for player profiles (page {page}): Missing or invalid 'response' key. Response: {data}")
            return None

        # بررسی اطلاعات صفحه‌بندی
        paging_info = data.get("paging", {})
        current_page_resp = paging_info.get("current", page)
        total_pages = paging_info.get("total", 1)
        logger.debug(f"Player profiles API response paging: current={current_page_resp}, total={total_pages} (Requested page {page})")

        # هشدار در صورت عدم تطابق صفحه بازگردانده‌شده
        if current_page_resp != page:
            logger.warning(f"API returned page {current_page_resp} when page {page} was requested.")

        return data  # بازگرداندن کل پاسخ شامل response و paging

    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching player profiles (page {page}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e: # (بدون تغییر)
        logger.exception(f"Unexpected error fetching player profiles (page {page}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for player profiles page {page}: {e}") from e


async def fetch_player_profile_by_id(external_player_id: int) -> Optional[Dict[str, Any]]:
    """
    پروفایل یک بازیکن خاص را با ID خارجی آن از API دریافت می‌کند.
    """
    endpoint = "/players/profiles"
    params = {"player": str(external_player_id)}
    logger.info(f"Fetching player profile from external API for external_id={external_player_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching player profile for id={external_player_id}: {data['errors']}")
            return None # یا خطای مناسب raise کنید

        response_list = data.get('response')
        if isinstance(response_list, list):
            # انتظار دقیقا یک نتیجه داریم
            if len(response_list) == 1:
                entry = response_list[0]
                # اعتبارسنجی پایه ورودی
                if isinstance(entry, dict) and 'player' in entry and isinstance(entry['player'], dict) and entry['player'].get('id') == external_player_id:
                    logger.info(f"Successfully fetched valid player profile entry from API for external_id={external_player_id}")
                    # خود آبجکت 'player' را برمی‌گردانیم
                    return entry['player']
                else:
                    logger.warning(f"Received invalid player profile entry or ID mismatch for external_id={external_player_id}. Data: {entry}")
                    return None
            elif len(response_list) == 0:
                 logger.warning(f"Player profile with external_id={external_player_id} not found in API (empty response list).")
                 return None
            else:
                 logger.error(f"Unexpected number of results ({len(response_list)}) fetching player profile by id={external_player_id}. Response: {data}")
                 # اولین مورد را برگردانیم یا None؟ فعلا None
                 return None
        else:
            logger.error(f"Invalid response structure for player profile (id={external_player_id}): Expected list under 'response', got {type(response_list)}. Response: {data}")
            return None

    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching player profile for id={external_player_id}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching player profile for id={external_player_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for player profile by id: {e}") from e
    

async def fetch_players_with_stats(league_id: int, season: int, page: int) -> Optional[Dict[str, Any]]:
    """
    یک صفحه از بازیکنان و آمار آنها را برای یک لیگ و فصل خاص از API دریافت می‌کند.
    """
    endpoint = "/players" # اندپوینت /players است، نه /players/profiles
    params = {
        "league": str(league_id),
        "season": str(season),
        "page": str(page)
    }
    logger.info(f"Fetching players with stats from external API (League: {league_id}, Season: {season}, Page: {page})")
    try:
        # این تابع کل دیکشنری پاسخ API را برمی‌گرداند
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching players/stats (L:{league_id}, S:{season}, P:{page}): {data['errors']}")
            # در صورت خطای rate limit یا مشابه، None برگردان تا سرویس مدیریت کند
            if 'rateLimit' in str(data['errors']):
                 raise TimeoutError("API Rate Limit Exceeded") # یا خطای سفارشی
            return None

        # بررسی اولیه ساختار پاسخ
        if 'response' not in data or not isinstance(data['response'], list):
             logger.error(f"Invalid response structure for players/stats (L:{league_id}, S:{season}, P:{page}): Response: {data}")
             return None

        # بررسی paging info
        paging_info = data.get("paging", {})
        current_page_resp = paging_info.get("current", page)
        total_pages = paging_info.get("total", 1)
        logger.debug(f"Players/Stats API response paging: current={current_page_resp}, total={total_pages} (Req: P{page})")

        # اعتبارسنجی پایه آیتم های response (اختیاری)
        if data['response']:
            first_item = data['response'][0]
            if not isinstance(first_item, dict) or 'player' not in first_item or 'statistics' not in first_item:
                logger.warning(f"Unexpected item structure in players/stats response (L:{league_id}, S:{season}, P:{page}). First item: {first_item}")

        return data # کل پاسخ شامل paging و response برگردانده می شود

    # مدیریت خطاهای اتصال / Timeout / ...
    except TimeoutError as te: # گرفتن خطای Rate limit که raise کردیم
         logger.error(f"API Rate Limit likely exceeded (L:{league_id}, S:{season}, P:{page})")
         raise te # دوباره raise کن تا سرویس مدیریت کند
    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching players/stats (L:{league_id}, S:{season}, P:{page}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching players/stats (L:{league_id}, S:{season}, P:{page}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for players/stats: {e}") from e
    

async def fetch_team_by_id(team_id: int) -> List[Dict[str, Any]]:
    """
    اطلاعات یک تیم خاص (شامل ورزشگاه) را بر اساس ID خارجی آن از API دریافت می‌کند.
    ساختار پاسخ API: {"team": {...}, "venue": {...}}
    """
    endpoint = "/teams"
    params = {"id": str(team_id)}
    logger.info(f"Fetching team from external API for external_id={team_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching team for id={team_id}: {data['errors']}")
            return None

        response_list = data.get('response')
        if isinstance(response_list, list):
             # فیلتر کردن ورودی‌های نامعتبر (مشابه قبل)
             valid_entries = [
                 entry for entry in response_list
                 if isinstance(entry, dict) and 'team' in entry and 'venue' in entry
                 and isinstance(entry.get('team'), dict) and entry['team'].get('id') is not None
                 and isinstance(entry.get('venue'), dict)
             ]
             if len(valid_entries) != len(response_list):
                  invalid_count = len(response_list) - len(valid_entries)
                  logger.warning(f"Found {invalid_count} invalid/incomplete team entries in API response")

             logger.info(f"Successfully fetched {len(valid_entries)} valid team entries from API")
             return valid_entries
        else:
             logger.error(f"Invalid response structure for teams")
             return []


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching team for id={team_id}: {api_error}", exc_info=True)
        raise api_error # اجازه دهید سرویس خطا را مدیریت کند
    except Exception as e:
        logger.exception(f"Unexpected error fetching team for id={team_id}: {e}")
        # تبدیل به خطای قابل مدیریت‌تر
        raise ConnectionError(f"Unexpected error connecting to API for team by id: {e}") from e


async def fetch_country_by_name(country_name: str) -> Optional[Dict[str, Any]]:
    """
    اطلاعات یک کشور خاص را بر اساس نام آن از API دریافت می‌کند.
    ساختار پاسخ API: {"name": "...", "code": "...", "flag": "..."}
    """
    endpoint = "/countries"
    params = {"name": country_name}
    logger.info(f"Fetching country from external API by name: '{country_name}'")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی خطاهای منطقی گزارش شده توسط خود API
        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching country by name '{country_name}': {data['errors']}")
            return None

        response_list = data.get('response')
        if isinstance(response_list, list):
            if len(response_list) == 1:
                entry = response_list[0]
                # اعتبارسنجی پایه ورودی (باید شامل name باشد)
                if isinstance(entry, dict) and entry.get('name') == country_name:
                    logger.info(f"Successfully fetched valid country entry from API for name: '{country_name}'")
                    # کل entry شامل name, code, flag را برمی‌گردانیم
                    return entry
                else:
                    logger.warning(f"Received invalid country entry or name mismatch for name: '{country_name}'. Data: {entry}")
                    return None
            elif len(response_list) == 0:
                 logger.warning(f"Country with name '{country_name}' not found in API (empty response list).")
                 return None
            else:
                 # اگر API بیش از یک نتیجه برای نام دقیق برگرداند، غیرمنتظره است
                 logger.error(f"Unexpected number of results ({len(response_list)}) fetching country by name '{country_name}'. Response: {data}")
                 return None # یا اولین مورد را برگردانیم؟ فعلا None
        else:
            logger.error(f"Invalid response structure for country (name='{country_name}'): Expected list under 'response', got {type(response_list)}. Response: {data}")
            return None

    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching country by name '{country_name}': {api_error}", exc_info=True)
        raise api_error # اجازه دهید سرویس خطا را مدیریت کند
    except Exception as e:
        logger.exception(f"Unexpected error fetching country by name '{country_name}': {e}")
        raise ConnectionError(f"Unexpected error connecting to API for country by name: {e}") from e


async def fetch_players_by_team(team_id: int) -> Dict[str, Any]:
    """
    Fetch players for a specific team from the API-Football service.
    """
    endpoint = "/players"
    params = {"team": team_id, "season": settings.CURRENT_SEASON}
    logger.info(f"Fetching players from external API for team ID: {team_id}")

    try:
        data = await _make_api_request("GET", endpoint, params=params)

        # بررسی ساختار پاسخ API
        response_list = data.get('response')
        if isinstance(response_list, list):
            logger.info(f"Successfully fetched {len(response_list)} players for team ID={team_id}")
            return data
        else:
            logger.error(f"Invalid response structure for players (team ID={team_id}): Expected list under 'response'. Response: {data}")
            return {}

    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching players for team ID={team_id}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching players for team ID={team_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for players by team ID: {e}") from e


async def fetch_fixtures_by_league_season(league_id: int, season: int) -> Optional[Dict[str, Any]]:
    endpoint = "/fixtures" 
    params = {
        "league": str(league_id),
        "season": str(season)
    }

    logger.info(f"Fetching fixtures from external API (League: {league_id}, Season: {season})")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching players/stats (L:{league_id}, S:{season}): {data['errors']}")
            if 'rateLimit' in str(data['errors']):
                 raise TimeoutError("API Rate Limit Exceeded") 
            return None

        if 'response' not in data or not isinstance(data['response'], list):
             logger.error(f"Invalid response structure for fixtures (L:{league_id}, S:{season}): Response: {data}")
             return None

        return data 

    except TimeoutError as te: 
         logger.error(f"API Rate Limit likely exceeded (L:{league_id}, S:{season})")
         raise te 
    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixtures (L:{league_id}, S:{season}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixtures (L:{league_id}, S:{season}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixtures: {e}") from e


async def fetch_lineups_by_id(match_id: int) -> List[Dict[str, Any]]:
    endpoint = "/fixtures/lineups"
    params = {"fixture": str(match_id)}
    logger.info(f"Fetching team from external API for external_id={match_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching fixture lineups for id={match_id}: {data['errors']}")
            return None
            
        return data 


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixture lineups for id={match_id}: {api_error}", exc_info=True)
        raise api_error 
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixture lineups for id={match_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixture lineups by id: {e}") from e

async def fetch_events_by_id(match_id: int) -> List[Dict[str, Any]]:
    endpoint = "/fixtures/events"
    params = {"fixture": str(match_id)}
    logger.info(f"Fetching events from external API for external_id={match_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching fixture events for id={match_id}: {data['errors']}")
            return None
          
        return data


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixture events for id={match_id}: {api_error}", exc_info=True)
        raise api_error 
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixture events for id={match_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixture events by id: {e}") from e


async def fetch_statistics_by_id(match_id: int) -> List[Dict[str, Any]]:
    endpoint = "/fixtures/statistics"
    params = {"fixture": str(match_id)}
    logger.info(f"Fetching statistics from external API for external_id={match_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching fixture statistics for id={match_id}: {data['errors']}")
            return None
     
        return data


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixture statistics for id={match_id}: {api_error}", exc_info=True)
        raise api_error 
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixture statistics for id={match_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixture statistics by id: {e}") from e


async def fetch_fixtures_by_ids(fixture_ids: List[int]) -> Optional[Dict[str, Any]]:
    if not fixture_ids:
        logger.warning("fetch_fixtures_by_ids called with an empty list of IDs.")
        return None 
    endpoint = "/fixtures"
    ids_str = '-'.join(map(str, fixture_ids))
    params = {"ids": ids_str}
    logger.info(f"Fetching fixtures from external API (ids: {ids_str})")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching Fixtures (ids: {ids_str}): {data['errors']}")
            if 'rateLimit' in str(data['errors']):
                 raise TimeoutError("API Rate Limit Exceeded") 
            return None

        if 'response' not in data or not isinstance(data['response'], list):
             logger.error(f"Invalid response structure for fixtures (ids: {ids_str}): Response: {data}")
             return None

        return data 

    except TimeoutError as te: 
         logger.error(f"API Rate Limit likely exceeded (ids: {ids_str})")
         raise te 
    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixtures (ids: {ids_str}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixtures (ids: {ids_str}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixtures: {e}") from e


async def fetch_fixture_player_stats(match_id: int) -> List[Dict[str, Any]]:
    endpoint = "/fixtures/players"
    params = {"fixture": str(match_id)}
    logger.info(f"Fetching fixture player stats from external API for external_id={match_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching fixture player stats for id={match_id}: {data['errors']}")
            return None
          
        return data


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching fixture player stats for id={match_id}: {api_error}", exc_info=True)
        raise api_error 
    except Exception as e:
        logger.exception(f"Unexpected error fetching fixture player stats for id={match_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for fixture player stats by id: {e}") from e


async def fetch_coach_by_id(external_coach_id: int) -> Optional[List[Dict[str, Any]]]:

    endpoint = "/coachs"
    params = {"id": str(external_coach_id)}
    logger.info(f"Fetching coach from external API for external_id={external_coach_id}")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching coach for id={external_coach_id}: {data['errors']}")
            return None 

        return data

    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching coach for id={external_coach_id}: {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching coach for id={external_coach_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for coach by id: {e}") from e
    

async def fetch_injuries_by_league_season(league_id: int, season: int) -> Optional[Dict[str, Any]]:
    endpoint = "/injuries" 
    params = {
        "league": str(league_id),
        "season": str(season)
    }

    logger.info(f"Fetching injuries from external API (League: {league_id}, Season: {season})")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching injuries (L:{league_id}, S:{season}): {data['errors']}")
            if 'rateLimit' in str(data['errors']):
                 raise TimeoutError("API Rate Limit Exceeded") 
            return None

        if 'response' not in data or not isinstance(data['response'], list):
             logger.error(f"Invalid response structure for injuries (L:{league_id}, S:{season}): Response: {data}")
             return None

        return data 

    except TimeoutError as te: 
         logger.error(f"API Rate Limit likely exceeded (L:{league_id}, S:{season})")
         raise te 
    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching injuries (L:{league_id}, S:{season}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching injuries (L:{league_id}, S:{season}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for injuries: {e}") from e


async def fetch_injuries_by_ids(injury_ids: List[int]) -> Optional[Dict[str, Any]]:
    if not injury_ids:
        logger.warning("fetch_injuries_by_ids called with an empty list of IDs.")
        return None 
    endpoint = "/injuries"
    ids_str = '-'.join(map(str, injury_ids))
    params = {"ids": ids_str}
    logger.info(f"Fetching injuries from external API (ids: {ids_str})")
    try:
        data = await _make_api_request("GET", endpoint, params=params)

        if data.get("errors") and (isinstance(data["errors"], list) and data["errors"] or isinstance(data["errors"], dict) and data["errors"]):
            logger.error(f"API reported errors fetching injuries (ids: {ids_str}): {data['errors']}")
            if 'rateLimit' in str(data['errors']):
                 raise TimeoutError("API Rate Limit Exceeded") 
            return None

        if 'response' not in data or not isinstance(data['response'], list):
             logger.error(f"Invalid response structure for injuries (ids: {ids_str}): Response: {data}")
             return None

        return data 

    except TimeoutError as te: 
         logger.error(f"API Rate Limit likely exceeded (ids: {ids_str})")
         raise te 
    except (ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching injuries (ids: {ids_str}): {api_error}", exc_info=True)
        raise api_error
    except Exception as e:
        logger.exception(f"Unexpected error fetching injuries (ids: {ids_str}): {e}")
        raise ConnectionError(f"Unexpected error connecting to API for injuries: {e}") from e
