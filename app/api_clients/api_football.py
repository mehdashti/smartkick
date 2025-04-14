# app/api_clients/api_football.py
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging 

logger = logging.getLogger(__name__)


BASE_URL = f"https://{settings.API_FOOTBALL_HOST}"
HEADERS = {
    'x-rapidapi-host': settings.API_FOOTBALL_HOST,
    'x-rapidapi-key': settings.API_FOOTBALL_KEY
}
DEFAULT_TIMEOUT = 15.0

async def _make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    expected_status: int = 200
) -> Dict[str, Any]:

    url = f"{BASE_URL}{endpoint}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=HEADERS,
                params=params,
                timeout=DEFAULT_TIMEOUT
            )

   
            if response.status_code != expected_status:
                 raise ValueError(f"API Error: Unexpected status code {response.status_code} from {url}. Body: {response.text[:500]}")

            try:
                return response.json()
            except ValueError as json_err:                 
                 raise ValueError(f"API Error: Failed to decode JSON response from {url}. Text: {response.text[:500]}") from json_err

        except httpx.TimeoutException as e:             
             raise TimeoutError(f"API Error: Request to {url} timed out.") from e
        except httpx.RequestError as e:
             raise ConnectionError(f"API Error: Network error connecting to {url} ({type(e).__name__}).") from e
        except Exception as e:
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

async def fetch_teams_info(team_id: int) -> Dict[str, Any]:

    endpoint = "/teams"
    params = {"id": team_id}
    data = await _make_api_request("GET", endpoint, params=params)

    response_list = data.get('response')
    if isinstance(response_list, list) and response_list:
        return response_list[0]
    else:
        raise LookupError(f"Team info not found or invalid response for ID: {team_id}")

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