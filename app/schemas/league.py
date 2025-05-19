# app/schemas/league.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.country import CountryOut
    from app.schemas.player_season_stats import PlayerSeasonStatsOut


class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class LeagueBase(APIModel):
    """Base schema for league data (core data fields)."""
    name: str = Field(..., min_length=2, max_length=100, description="League's full name")
    type: str = Field(..., pattern="^(League|Cup)$", description="Type of competition")
    logo_url: Optional[HttpUrl | str] = Field(None, description="URL of the league's logo")

class LeagueAPIInputData(APIModel):
    """Validates the structure of league data directly from the API."""
    league: Dict[str, Any] = Field(..., description="League data from external API")
    country: Dict[str, Any] = Field(..., description="Country data from external API")
    seasons: List[Dict[str, Any]] = Field(..., description="List of seasons data")

class LeagueCreateInternal(LeagueBase):
    """Schema used internally for creating/updating leagues."""
    league_id: int = Field(..., description="League ID from the external API")
    season: int = Field(..., ge=1900, le=2100, description="Season year")
    start_date: date = Field(..., description="Start date of the season")
    end_date: date = Field(..., description="End date of the season")
    country_id: int = Field(..., description="Internal country ID")
    is_current: bool = Field(False, description="Is current season")
    
    # Coverage flags
    has_standings: bool = Field(False)
    has_players: bool = Field(False)
    has_top_scorers: bool = Field(False)
    has_top_assists: bool = Field(False)
    has_top_cards: bool = Field(False)
    has_injuries: bool = Field(False)
    has_predictions: bool = Field(False)
    has_odds: bool = Field(False)
    has_events: bool = Field(False)
    has_lineups: bool = Field(False)
    has_fixture_stats: bool = Field(False)
    has_player_stats: bool = Field(False)

class LeagueUpdate(APIModel):
    """Schema for partially updating an existing league."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    type: Optional[str] = Field(None, pattern="^(League|Cup)$")
    logo_url: Optional[HttpUrl | str] = None
    is_current: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Optional coverage flags
    has_standings: Optional[bool] = None
    has_players: Optional[bool] = None
    has_top_scorers: Optional[bool] = None
    has_top_assists: Optional[bool] = None
    has_top_cards: Optional[bool] = None
    has_injuries: Optional[bool] = None
    has_predictions: Optional[bool] = None
    has_odds: Optional[bool] = None
    has_events: Optional[bool] = None
    has_lineups: Optional[bool] = None
    has_fixture_stats: Optional[bool] = None
    has_player_stats: Optional[bool] = None

class LeagueOut(LeagueBase):
    """Schema for representing a league in API responses."""
    id: int = Field(..., description="League ID (Primary Key)")
    league_id: int = Field(..., description="External API league ID")
    season: int = Field(...)
    start_date: date = Field(...)
    end_date: date = Field(...)
    country_id: int = Field(...)
    is_current: bool = Field(...)
    created_at: datetime
    updated_at: datetime
    
    # Coverage flags
    has_standings: bool = Field(...)
    has_players: bool = Field(...)
    has_top_scorers: bool = Field(...)
    has_top_assists: bool = Field(...)
    has_top_cards: bool = Field(...)
    has_injuries: bool = Field(...)
    has_predictions: bool = Field(...)
    has_odds: bool = Field(...)
    has_events: bool = Field(...)
    has_lineups: bool = Field(...)
    has_fixture_stats: bool = Field(...)
    has_player_stats: bool = Field(...)
    
    # Relationships
    country: Optional["CountryOut"] = None
    seasons_stats: Optional[List["PlayerSeasonStatsOut"]] = None

class LeagueProfileApiResponseItem(APIModel):
    league: Dict[str, Any] = Field(..., description="Raw league data from API")

class LeagueProfileApiResponse(APIModel):
    response: List[LeagueProfileApiResponseItem]

class LeagueWithSeasonsApiResponseItem(APIModel):
    league: Dict[str, Any]
    seasons: List[Dict[str, Any]]

class LeagueWithSeasonsApiResponse(APIModel):
    response: List[LeagueWithSeasonsApiResponseItem]
    paging: Optional[Dict[str, int]] = None

# حلقه‌های ارجاعی
#LeagueOut.model_rebuild()
#LeagueWithSeasonsApiResponseItem.model_rebuild()