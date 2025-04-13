# api_clients/api_football.py
import httpx
import requests
from typing import List 
from .errors import APIFootballError, InvalidAPIResponseError 
from app.core.config import settings

BASE_URL = f"https://{settings.API_FOOTBALL_HOST}"

# هدرها رو اینجا تعریف می‌کنیم چون مختص این API هستند
headers = {
    'x-rapidapi-host': settings.API_FOOTBALL_HOST,
    'x-rapidapi-key': settings.API_FOOTBALL_KEY
}

class APIFootballError(Exception):
    """خطای سفارشی برای مشکلات مربوط به API-Football."""
    pass

class PlayerNotFoundError(APIFootballError):
    """خطای سفارشی وقتی بازیکن پیدا نمی‌شود."""
    pass


async def fetch_player_teams(player_id: int):

    player_endpoint = f"{BASE_URL}/players/teams?player={player_id}"
    params = {
        "id": player_id,

    }

    try:
        response = requests.get(player_endpoint, headers=headers)
        response.raise_for_status() # بررسی خطاهای HTTP (4xx, 5xx)

        data = response.json()

        if not data.get('response') or not data['response']:
            raise PlayerNotFoundError(f"بازیکن با شناسه {player_id} پیدا نشد.")
        return data['response'][0]

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        print(f"HTTP Error from API-Football: {status_code} - {e.response.text}")
        raise APIFootballError(f"خطای HTTP {status_code} از API-Football دریافت شد.") from e

    except requests.exceptions.RequestException as e:
        print(f"خطای ارتباط با API-Football: {e}")
        raise APIFootballError("خطا در برقراری ارتباط با سرویس API-Football.") from e

    except Exception as e:
        print(f"خطای پیش‌بینی نشده در api_football.py: {e}")
        raise APIFootballError("یک خطای ناشناخته در پردازش پاسخ API-Football رخ داد.") from e


async def fetch_teams_info(team_id: int):

    team_endpoint = f"{BASE_URL}/teams?id={team_id}"
    params = {
        "id": team_id,

    }

    try:
        response = requests.get(team_endpoint, headers=headers)
        response.raise_for_status() # بررسی خطاهای HTTP (4xx, 5xx)

        data = response.json()

        if not data.get('response') or not data['response']:
            raise PlayerNotFoundError(f"بازیکن با شناسه {team_id} پیدا نشد.")
        return data['response'][0]

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        print(f"HTTP Error from API-Football: {status_code} - {e.response.text}")
        raise APIFootballError(f"خطای HTTP {status_code} از API-Football دریافت شد.") from e

    except requests.exceptions.RequestException as e:
        print(f"خطای ارتباط با API-Football: {e}")
        raise APIFootballError("خطا در برقراری ارتباط با سرویس API-Football.") from e

    except Exception as e:
        print(f"خطای پیش‌بینی نشده در api_football.py: {e}")
        raise APIFootballError("یک خطای ناشناخته در پردازش پاسخ API-Football رخ داد.") from e


async def fetch_timezones_from_api() -> list[str]:
    timezone_endpoint = f"{BASE_URL}/timezone"
    print(f"[API Client] Fetching timezones from: {timezone_endpoint}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(timezone_endpoint, headers=headers) 
            response.raise_for_status() 

            data = response.json()

            response_list = data.get('response') 

            if isinstance(response_list, list):

                return response_list # ---> برگرداندن لیست استخراج شده


        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            print(f"[API Client] HTTP Error fetching timezones: {status_code} - {e.response.text}")
            # می توانید بر اساس status_code خطای خاص تری raise کنید
            # if status_code == 401 or status_code == 403:
            #     raise APIAuthenticationError(...)
            # if status_code == 429:
            #     raise APILimitExceededError(...)
            raise APIFootballError(f"خطای HTTP {status_code} هنگام دریافت timezone ها.") from e
        except httpx.RequestError as e:
            print(f"[API Client] Request Error fetching timezones: {e}")
            raise APIFootballError("خطا در برقراری ارتباط با سرویس API-Football برای دریافت timezone ها.") from e
        except ValueError as e: # خطای JSONDecodeError از ValueError ارث بری می کند
             print(f"[API Client] Error decoding JSON response: {e}")
             raise InvalidAPIResponseError("پاسخ دریافت شده از API قابل تبدیل به JSON نبود.") from e
        except Exception as e:
            print(f"[API Client] Unexpected error fetching timezones: {e}")
            # بررسی کنید آیا این خطا از نوع APIFootballError است یا نه
            if isinstance(e, APIFootballError):
                raise # اگر خطای خودمان بود دوباره raise کن
            else:
                # در غیر این صورت به عنوان خطای عمومی APIFootballError گزارش کن
                raise APIFootballError(f"یک خطای ناشناخته هنگام پردازش timezone ها رخ داد: {type(e).__name__} - {e}") from e