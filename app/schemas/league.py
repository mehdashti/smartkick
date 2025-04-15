# app/schemas/country.py
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from .country import CountryOut  # assuming CountryOut is already defined

class LeagueBase(BaseModel):
    """Base schema for League (common fields)"""
    name: str = Field(..., min_length=2, max_length=100, description="Full name of the league")
    season: int = Field(..., gt=1900, lt=2100, description="Season year of the league")
    type: str = Field(..., pattern="^(League|Cup|Tournament)$", description="Type of the league")
    start_date: date = Field(..., description="Start date of the season")
    end_date: date = Field(..., description="End date of the season")
    country_id: int = Field(..., description="ID of the associated country")

class LeagueCreate(LeagueBase):
    """Schema for creating a new league"""
    external_id: Optional[int] = Field(None, description="External ID from a data provider")
    is_current: bool = Field(False, description="Whether the season is currently active")
    logo_url: Optional[str] = Field(None, max_length=255, description="URL of the league logo")
    
    has_standings: bool = Field(False, description="Whether standings data is available")
    has_players: bool = Field(False, description="Whether player data is available")
    has_top_scorers: bool = Field(False, description="Whether top scorers data is available")
    has_top_assists: bool = Field(False, description="Whether top assists data is available")
    has_top_cards: bool = Field(False, description="Whether top cards data is available")
    has_injuries: bool = Field(False, description="Whether injury data is available")
    has_predictions: bool = Field(False, description="Whether predictions are available")
    has_odds: bool = Field(False, description="Whether betting odds are available")
    has_events: bool = Field(False, description="Whether match event data is available")
    has_lineups: bool = Field(False, description="Whether team lineups are available")
    has_fixture_stats: bool = Field(False, description="Whether fixture statistics are available")
    has_player_stats: bool = Field(False, description="Whether player statistics are available")

class LeagueUpdate(BaseModel):
    """Schema for updating an existing league"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    season: Optional[int] = Field(None, gt=1900, lt=2100)
    is_current: Optional[bool] = None
    type: Optional[str] = Field(None, pattern="^(League|Cup|Tournament)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    logo_url: Optional[str] = Field(None, max_length=255)
    
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
    """Schema for outputting league data"""
    league_id: int = Field(..., description="Primary ID of the league")
    external_id: Optional[int] = None
    is_current: bool = Field(..., description="Whether the season is currently active")
    logo_url: Optional[str] = Field(None, description="URL of the league logo")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    country: Optional[CountryOut] = Field(None, description="Associated country data")
    
    has_standings: bool = Field(..., description="Whether standings data is available")
    has_players: bool = Field(..., description="Whether player data is available")
    has_top_scorers: bool = Field(..., description="Whether top scorers data is available")
    has_top_assists: bool = Field(..., description="Whether top assists data is available")
    has_top_cards: bool = Field(..., description="Whether top cards data is available")
    has_injuries: bool = Field(..., description="Whether injury data is available")
    has_predictions: bool = Field(..., description="Whether predictions are available")
    has_odds: bool = Field(..., description="Whether betting odds are available")
    has_events: bool = Field(..., description="Whether match event data is available")
    has_lineups: bool = Field(..., description="Whether team lineups are available")
    has_fixture_stats: bool = Field(..., description="Whether fixture statistics are available")
    has_player_stats: bool = Field(..., description="Whether player statistics are available")
    
    model_config = ConfigDict(from_attributes=True)

class LeagueWithCoverage(LeagueOut):
    """Schema for outputting league data with additional coverage details"""
    coverage_details: Optional[dict] = Field(
        None,
        description="Additional information about league coverage"
    )
