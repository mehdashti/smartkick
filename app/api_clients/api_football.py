# app/api_clients/api_football.py
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging
import asyncio 
import time    
import collections 

logger = logging.getLogger(__name__)


BASE_URL = f"https://{settings.API_FOOTBALL_HOST}"
HEADERS = {
    'x-rapidapi-host': settings.API_FOOTBALL_HOST,
    'x-rapidapi-key': settings.API_FOOTBALL_KEY
}
DEFAULT_TIMEOUT = 15.0

# --- Rate Limiting State ---
_REQUEST_TIMESTAMPS = collections.deque()
_RATE_LIMIT_LOCK = asyncio.Lock()
# خواندن مقادیر از تنظیمات (مطمئن شوید این مقادیر در settings.py تعریف شده‌اند)
_MAX_REQUESTS = getattr(settings, 'API_FOOTBALL_MAX_REQUESTS_PER_MINUTE', 30) # مثال: 30 درخواست
_PERIOD_SECONDS = getattr(settings, 'API_FOOTBALL_RATE_LIMIT_PERIOD_SECONDS', 60.0) # مثال: 60 ثانیه

async def _wait_for_rate_limit():
    """Checks and waits for the rate limit if necessary before making a request."""
    async with _RATE_LIMIT_LOCK:
        while True:
            now = time.monotonic()
            # Remove timestamps older than the period
            while _REQUEST_TIMESTAMPS and (now - _REQUEST_TIMESTAMPS[0] > _PERIOD_SECONDS):
                _REQUEST_TIMESTAMPS.popleft()

            if len(_REQUEST_TIMESTAMPS) < _MAX_REQUESTS:
                _REQUEST_TIMESTAMPS.append(now)
                logger.debug(f"Rate limit check passed. Current count: {len(_REQUEST_TIMESTAMPS)}/{_MAX_REQUESTS}")
                break # Exit the loop, request can proceed
            else:
                # Calculate wait time until the oldest request expires
                oldest_request_time = _REQUEST_TIMESTAMPS[0]
                wait_time = (_PERIOD_SECONDS - (now - oldest_request_time)) + 0.1 # Add a small buffer
                wait_time = max(0, wait_time) # Ensure wait_time is not negative

                logger.warning(
                    f"Rate limit reached ({len(_REQUEST_TIMESTAMPS)}/{_MAX_REQUESTS} in last {_PERIOD_SECONDS}s). "
                    f"Waiting for {wait_time:.2f} seconds."
                )
                # Keep the lock while sleeping to prevent other tasks from immediately
                # hitting the limit again. This serializes the waiting tasks.
                await asyncio.sleep(wait_time)
                # Loop continues to re-evaluate after waking up

async def _make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    expected_status: int = 200
) -> Dict[str, Any]:
    """Makes a rate-limited request to the API-Football endpoint."""

    # --- Wait for rate limit before making the request ---
    await _wait_for_rate_limit()
    # -----------------------------------------------------

    url = f"{BASE_URL}{endpoint}"
    # Use a shared client instance if possible for performance (connection pooling)
    # If not shared, create it here:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        try:
            logger.debug(f"Sending API request: {method} {url} Params: {params}")
            response = await client.request(
                method=method,
                url=url,
                headers=HEADERS,
                params=params,
                # timeout=DEFAULT_TIMEOUT # Timeout is set on the client now
            )

            # Check for specific rate limit status code (e.g., 429) if the API uses it
            if response.status_code == 429:
                 # You might want to handle this more gracefully, perhaps by retrying
                 # after the duration specified in Retry-After header, if available.
                 # For now, we treat it like other unexpected statuses.
                 logger.error(f"API Error: Rate limit explicitly hit (429 Too Many Requests) from {url}. Body: {response.text[:500]}")
                 # Raising ValueError might not be ideal, maybe a custom exception?
                 raise ValueError(f"API Error: Rate limit explicitly hit (429) from {url}.")


            if response.status_code != expected_status:
                 logger.error(f"API Error: Unexpected status code {response.status_code} from {url}. Body: {response.text[:500]}")
                 # Consider raising a more specific error based on status code (e.g., 401, 403, 404)
                 raise ValueError(f"API Error: Unexpected status code {response.status_code} from {url}.")

            try:
                data = response.json()
                logger.debug(f"Received successful API response ({response.status_code}) from {url}")
                return data
            except ValueError as json_err:
                 logger.error(f"API Error: Failed to decode JSON response from {url}. Status: {response.status_code}, Text: {response.text[:500]}")
                 raise ValueError(f"API Error: Failed to decode JSON response from {url}.") from json_err

        except httpx.TimeoutException as e:
             logger.error(f"API Error: Request to {url} timed out after {DEFAULT_TIMEOUT} seconds.")
             raise TimeoutError(f"API Error: Request to {url} timed out.") from e
        except httpx.RequestError as e:
             # Includes connection errors, DNS errors, etc.
             logger.error(f"API Error: Network error connecting to {url}. Error: {e}")
             raise ConnectionError(f"API Error: Network error connecting to {url} ({type(e).__name__}).") from e
        except ValueError as ve: # Catch the ValueErrors we raised
             # Logged above, just re-raise
             raise ve
        except Exception as e:
             # Catch-all for truly unexpected errors
             logger.exception(f"API Error: Unexpected error during request to {url}: {e}")
             # Re-raise as a standard exception or a custom API error
             raise Exception(f"API Error: Unexpected error during request to {url}: {e}") from e


async def fetch_player_teams(player_id: int) -> Dict[str, Any]:

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

        response_list = data.get('response')
            
        return response_list 


    except (ValueError, ConnectionError, TimeoutError) as api_error:
        logger.error(f"API Error fetching team for id={match_id}: {api_error}", exc_info=True)
        raise api_error 
    except Exception as e:
        logger.exception(f"Unexpected error fetching team for id={match_id}: {e}")
        raise ConnectionError(f"Unexpected error connecting to API for team by id: {e}") from e
