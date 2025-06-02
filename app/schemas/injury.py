# app/schemas/injury.py
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from app.schemas.coach_careers import CoachCareersOut

# --- Base Config ---
class APIModel(BaseModel):
    """Base model with common config for all schemas"""
    model_config = ConfigDict(
        from_attributes=True,  
        populate_by_name=True, 
        alias_generator=to_camel  
    )

# --- Base Schema ---
class InjuryBase(APIModel):
    player_id: int = Field(..., description="Player ID")
    team_id: int = Field(..., description="Team ID")
    match_id: int = Field(..., description="Match ID")
    league_id: int = Field(..., description="League ID")
    season: int = Field(..., description="Season")  # Changed from str to int
    type: str = Field(..., description="Type of injury")
    reason: str = Field(..., description="Reason for the injury")

# --- API Input Schema ---
class PlayerInjuryData(APIModel):
    id: Optional[int] = None
    name: Optional[str] = None
    photo: Optional[HttpUrl] = None  # Made HttpUrl primary type
    type: Optional[str] = None
    reason: Optional[str] = None

class TeamData(APIModel):
    id: Optional[int] = None
    name: Optional[str] = None
    logo: Optional[HttpUrl] = None  # Made HttpUrl primary type

class FixtureData(APIModel):
    id: Optional[int] = None
    timezone: Optional[str] = None
    date: Optional[str] = None
    timestamp: Optional[int] = None
    
class LeagueData(APIModel):
    id: Optional[int] = None
    season: Optional[int] = None  # Changed from str to int to match API response
    name: Optional[str] = None
    country: Optional[str] = None
    logo: Optional[HttpUrl] = None  # Made HttpUrl primary type
    flag: Optional[HttpUrl] = None  # Made HttpUrl primary type

class InjuryApiResponseItem(APIModel):
    player: Optional[PlayerInjuryData] = None  # Changed from Dict to direct class
    team: Optional[TeamData] = None  # Changed from Dict to direct class
    fixture: Optional[FixtureData] = None  # Changed from Dict to direct class
    league: Optional[LeagueData] = None  # Changed from Dict to direct class

class InjuryApiResponse(APIModel):
    get: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    errors: List[Any] = Field(default_factory=list)
    results: Optional[int] = None
    paging: Optional[Dict[str, int]] = None
    response: List[InjuryApiResponseItem]

# --- Internal Create/Update Schema ---
class InjuryCreateInternal(InjuryBase):
    """Schema for creating a new injury."""
    pass

class InjuryUpdateInternal(InjuryBase):
    """Schema for updating an existing injury."""
    pass

# --- Output Schema ---
class InjuryOut(InjuryBase):
    """Schema for representing an injury in API responses."""
    pass