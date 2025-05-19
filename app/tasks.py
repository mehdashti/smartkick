import logging
from celery import shared_task
from app.services.player_service import PlayerService
from app.services.metadata_service import MetadataService
from app.services.team_service import TeamService
from app.services.league_service import LeagueService
from app.services.venue_service import VenueService

logger = logging.getLogger(__name__)

metadata_service = MetadataService()
team_service = TeamService()
league_service = LeagueService()
venue_service = VenueService()
player_service = PlayerService()

@shared_task(name="update_timezones_task")
def update_timezones_task():
    """
    Celery task to update timezones from the external API.
    """
    return {"status": "delegated", "task": "update_timezones"}

@shared_task(name="update_countries_task")
def update_countries_task():
    """
    Celery task to update countries from the external API.
    """
    return {"status": "delegated", "task": "update_countries"}

@shared_task(name="update_teams_by_country_task")
def update_teams_by_country_task(country_name: str):
    """
    Celery task to update teams and venues for a specific country.
    """
    return {"status": "delegated", "target": country_name}

@shared_task(name="update_teams_by_league_season_task")
def update_teams_by_league_season_task(league_id: int, season: int):
    """
    Celery task to update teams and venues for a specific league and season.
    """
    return {"status": "delegated", "league_id": league_id, "season": season}

@shared_task(name="update_leagues_task")
def update_leagues_task():
    """
    Celery task to update leagues and their seasons from the external API.
    """
    return {"status": "delegated", "task": "update_leagues"}

@shared_task(name="update_venues_by_country_task")
def update_venues_by_country_task(country_name: str):
    """
    Celery task to update venues for a specific country.
    """
    return {"status": "delegated", "target": country_name}

@shared_task(name="update_player_by_id_task")
def update_player_by_id_task(player_id: int):
    """
    Celery task to update a single player's profile by their external ID.
    """
    return {"status": "delegated", "player_id": player_id}

@shared_task(name="update_player_profiles_task")
def update_player_profiles_task():
    """
    Celery task to update all player profiles from the external API.
    """
    return {"status": "delegated", "task": "update_player_profiles"}

@shared_task(name="update_player_stats_for_league_season_task")
def update_player_stats_for_league_season_task(league_id: int, season: int, **kwargs):
    """
    Celery task to update player stats for a specific league and season.
    """
    return {"status": "delegated", "league_id": league_id, "season": season}

@shared_task(name="update_player_stats_for_league_task")
def update_player_stats_for_league_task(league_id: int, **kwargs):
    """
    Celery task to update player stats for all seasons of a specific league.
    """
    return {"status": "delegated", "league_id": league_id}

@shared_task(name="update_player_stats_for_season_task")
def update_player_stats_for_season_task(season: int, **kwargs):
    """
    Celery task to update player stats for all leagues in a specific season.
    """
    return {"status": "delegated", "season": season}
