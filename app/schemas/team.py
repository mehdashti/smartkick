# app/schemas/team.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.country import CountryOut
    from app.schemas.league import LeagueOut
    from app.schemas.venue import VenueOut

class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore"
    )

class TeamBase(APIModel):
    """Base schema for team data"""
    name: str = Field(..., max_length=100, description="Full team name")
    code: Optional[str] = Field(None, max_length=10, description="Short team code (3 letters)")
    founded: Optional[int] = Field(None, gt=1800, lt=2100, description="Year of foundation")
    is_national: bool = Field(..., description="Whether it's a national team")
    logo_url: Optional[HttpUrl | str] = Field(None, description="URL of team logo")

class TeamAPIInputData(APIModel):
    """Validates the structure of team data directly from the API"""
    team: Dict[str, Any] = Field(..., description="Raw team data from API")
    venue: Optional[Dict[str, Any]] = Field(None, description="Venue data from API")

class TeamCreateInternal(APIModel):
    """Schema used internally for creating teams"""
    team_id: int = Field(..., description="External API team ID")
    name: str = Field(..., max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    founded: Optional[int] = Field(None, gt=1800, lt=2100)
    is_national: bool = Field(...)
    logo_url: Optional[HttpUrl | str] = Field(None)
    country: Optional[str] = Field(None, max_length=255, description="Country name")
    venue_id: Optional[int] = Field(None, description="Internal venue ID")

class TeamUpdate(APIModel):
    """Schema for updating team data"""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    founded: Optional[int] = Field(None, gt=1800, lt=2100)
    is_national: Optional[bool] = None
    logo_url: Optional[HttpUrl | str] = None
    country: Optional[str] = Field(None, max_length=255)
    venue_id: Optional[int] = None

class TeamOut(TeamBase):
    """Output schema for team data"""
    team_id: int = Field(..., description="Internal team ID")
    country: Optional[str] = Field(None, max_length=255, description="Country name")
    venue_id: Optional[int] = Field(None, description="Associated venue ID")
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    country_details: Optional["CountryOut"] = Field(None, description="Country details", alias="country")
    venue: Optional["VenueOut"] = Field(None, description="Venue details")
    leagues: Optional[List["LeagueOut"]] = Field(None, description="Leagues team participates in")
    lineups: Optional[List["MatchLineupOut"]] = Field(None, description="Historical lineups for this team")

class TeamSummaryOut(APIModel):
    """Compact team representation for lists"""
    team_id: int
    name: str
    logo_url: Optional[HttpUrl | str] = None
    country: Optional[str] = Field(None, max_length=255, description="Country name")
    country_code: Optional[str] = None

class TeamListResponse(APIModel):
    """Paginated list of teams"""
    count: int = Field(..., description="Total number of teams")
    items: List[TeamOut] = Field(..., description="List of team records")